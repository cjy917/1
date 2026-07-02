package edu.xt1.spark

import org.apache.spark.ml.feature.{HashingTF, IDF, Tokenizer}
import org.apache.spark.ml.linalg.Vector
import org.apache.spark.sql.functions._
import org.apache.spark.sql.SparkSession

/**
 * 基于内容的电影推荐：TF-IDF + 余弦相似度
 * 仅对 ratings 与片库交集中的电影预计算相似邻居，并用 Spark 并行 + 预计算向量避免 Driver O(n^2) 卡数小时。
 */
object MovieRecommendContentBased {
  case class Rating(userId: Long, movieId: String, rating: Double)

  private case class VecEntry(id: String, arr: Array[Double], norm: Double)

  private def cosineSimFast(a1: Array[Double], n1: Double, a2: Array[Double], n2: Double): Double = {
    if (n1 == 0.0 || n2 == 0.0) return 0.0
    var dot = 0.0
    var i = 0
    val len = math.min(a1.length, a2.length)
    while (i < len) {
      dot += a1(i) * a2(i)
      i += 1
    }
    dot / (n1 * n2)
  }

  private def findEntry(cat: Array[VecEntry], id: String): VecEntry = {
    var i = 0
    while (i < cat.length) {
      if (cat(i).id == id) return cat(i)
      i += 1
    }
    throw new NoSuchElementException(s"movieId not in catalog: $id")
  }

  /** 对单部电影在 catalog 中取 Top-K 最相似邻居 */
  private def topKSimilar(e1: VecEntry, catalog: Array[VecEntry], k: Int): Seq[(String, Double)] = {
    val buf = new Array[(String, Double)](catalog.length - 1)
    var bi = 0
    var j = 0
    while (j < catalog.length) {
      val e2 = catalog(j)
      if (e2.id != e1.id) {
        buf(bi) = (e2.id, cosineSimFast(e1.arr, e1.norm, e2.arr, e2.norm))
        bi += 1
      }
      j += 1
    }
    buf.take(bi).sortBy(-_._2).take(k)
  }

  def main(args: Array[String]): Unit = {
    val moviesPath = if (args.length > 0) args(0) else "data/movies_catalog.ndjson"
    val ratingsPath = if (args.length > 1) args(1) else "data/ratings.json"
    val outputPath = if (args.length > 2) args(2) else "output/recommendations_content.json"
    val topN = 10

    val spark = SparkSession.builder()
      .appName("MovieRecommendContentBased")
      .master(sys.env.getOrElse("SPARK_MASTER", "local[*]"))
      .config("spark.hadoop.fs.defaultFS", "file:///")
      .getOrCreate()

    import spark.implicits._

    val ratingsUri = SparkLocalPaths.toUri(ratingsPath)
    val ratings = spark.read.json(ratingsUri).as[Rating].collect()
    val seedMovieIds = ratings.map(_.movieId).distinct.toSet

    val moviesUri = SparkLocalPaths.toUri(moviesPath)
    val movies = spark.read.json(moviesUri)
      .select(
        col("movieId").cast("string").alias("movieId"),
        col("featureText").alias("featureText")
      )
      .filter(col("movieId").isNotNull && col("featureText").isNotNull)
      .dropDuplicates("movieId")

    val tokenizer = new Tokenizer().setInputCol("featureText").setOutputCol("words")
    val hashingTF = new HashingTF().setInputCol("words").setOutputCol("rawFeatures").setNumFeatures(4096)
    val idf = new IDF().setInputCol("rawFeatures").setOutputCol("features")

    val tokenized = tokenizer.transform(movies)
    val featurized = hashingTF.transform(tokenized)
    val idfModel = idf.fit(featurized)
    val tfidfRows = idfModel.transform(featurized).select("movieId", "features").collect()

    val catalog: Array[VecEntry] = tfidfRows.map { row =>
      val id = row.getString(0)
      val arr = row.getAs[Vector](1).toArray
      var sq = 0.0
      var i = 0
      while (i < arr.length) {
        sq += arr(i) * arr(i)
        i += 1
      }
      VecEntry(id, arr, math.sqrt(sq))
    }

    val seedsToIndex = catalog.filter(e => seedMovieIds.contains(e.id)).map(_.id)
    println(s"TF-IDF vectors: ${catalog.length}, seed movies in ratings: ${seedMovieIds.size}, indexing: ${seedsToIndex.length}")

    val t0 = System.currentTimeMillis()
    println("Building similarity index (Spark parallel)...")

    val catalogBC = spark.sparkContext.broadcast(catalog)
    val partitions = math.max(4, spark.sparkContext.defaultParallelism)

    val similarIndex = spark.sparkContext
      .parallelize(seedsToIndex, partitions)
      .map { id1 =>
        val cat = catalogBC.value
        id1 -> topKSimilar(findEntry(cat, id1), cat, 30)
      }
      .collectAsMap()
      .toMap

    val elapsed = (System.currentTimeMillis() - t0) / 1000.0
    println(f"Similarity index built for ${similarIndex.size} seed movies in $elapsed%.1fs.")

    val userRatings = ratings.groupBy(_.userId)

    val results = userRatings.flatMap { case (userId, userRatingList) =>
      val ratedIds = userRatingList.map(_.movieId).toSet
      val aggregated = scala.collection.mutable.Map[String, Double]()

      userRatingList.foreach { r =>
        similarIndex.get(r.movieId).foreach { neighbors =>
          neighbors.foreach { case (mid, sim) =>
            if (!ratedIds.contains(mid) && sim > 0.01) {
              aggregated(mid) = aggregated.getOrElse(mid, 0.0) + sim * (r.rating / 10.0)
            }
          }
        }
      }

      aggregated.toSeq.sortBy(-_._2).take(topN).map { case (movieId, score) =>
        s"""{"userId":$userId,"movieId":"$movieId","score":$score}"""
      }
    }

    import java.nio.file.{Files, Paths}
    Files.createDirectories(Paths.get(outputPath).getParent)
    Files.write(
      Paths.get(outputPath),
      s"""{"algorithm":"content","items":[${results.mkString(",")}]}""".getBytes("UTF-8")
    )

    println(s"Content-based recommendations saved to $outputPath (${results.size} items)")
    spark.stop()
  }
}
