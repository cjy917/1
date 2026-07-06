package edu.xt1.spark

import org.apache.spark.ml.feature.{HashingTF, IDF, Tokenizer}
import org.apache.spark.ml.linalg.Vector
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.col

import java.nio.file.{Files, Paths}
import SparkRecommendCommon.Rating

/**
 * 离线预计算 Content 相似度索引与 GraphX 历史缓存（基于 ratings_history.ndjson）。
 * 历史评分不变时只需运行一次；刷新推荐时复用缓存。
 */
object MovieBuildSparkCaches {
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
    val historyPath = if (args.length > 1) args(1) else "data/ratings_history.ndjson"
    val contentIndexPath = if (args.length > 2) args(2) else "output/content_similarity_index.ndjson"
    val graphxCachePath = if (args.length > 3) args(3) else "output/graphx_history_cache.ndjson"

    val spark = SparkSession.builder()
      .appName("MovieBuildSparkCaches")
      .master(sys.env.getOrElse("SPARK_MASTER", "local[*]"))
      .config("spark.hadoop.fs.defaultFS", "file:///")
      .getOrCreate()

    import spark.implicits._

    val history = SparkRecommendCommon.readRatingsNdjson(historyPath)
    println(s"History ratings loaded: ${history.size}")

    // ----- Content similarity index -----
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

    val featurized = hashingTF.transform(tokenizer.transform(movies))
    val tfidfRows = idf.fit(featurized).transform(featurized).select("movieId", "features").collect()

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

    def findEntry(id: String): VecEntry = catalog.find(_.id == id).getOrElse(
      throw new NoSuchElementException(s"movieId not in catalog: $id")
    )

    val seedMovieIds = history.map(_.movieId).distinct.toSet
    val seedsToIndex = catalog.filter(e => seedMovieIds.contains(e.id)).map(_.id)
    println(s"Building content index for ${seedsToIndex.length} seed movies...")

    val indexLines = seedsToIndex.map { id1 =>
      val neighbors = topKSimilar(findEntry(id1), catalog, 30)
      val nbJson = neighbors.map { case (mid, sim) => s"""["$mid",$sim]""" }.mkString(",")
      s"""{"movieId":"$id1","neighbors":[$nbJson]}"""
    }

    val contentOut = Paths.get(contentIndexPath)
    Files.createDirectories(contentOut.getParent)
    Files.write(contentOut, indexLines.mkString("\n").getBytes("UTF-8"))
    println(s"Content index saved: $contentIndexPath (${indexLines.size} lines)")

    // ----- GraphX history cache (movie -> users, user -> ratings) -----
    val movieUsers = history.groupBy(_.movieId).map { case (mid, rs) =>
      val users = rs.map(r => s"""[${r.userId},${r.rating}]""").mkString(",")
      s"""{"movieId":"$mid","users":[$users]}"""
    }

    val userRatings = history.groupBy(_.userId).map { case (uid, rs) =>
      val ratings = rs.map(r => s"""["${r.movieId}",${r.rating}]""").mkString(",")
      s"""{"userId":$uid,"ratings":[$ratings]}"""
    }

    val graphxOut = Paths.get(graphxCachePath)
    Files.write(graphxOut, (movieUsers ++ userRatings).mkString("\n").getBytes("UTF-8"))
    println(s"GraphX cache saved: $graphxCachePath (${movieUsers.size} movies, ${userRatings.size} users)")

    spark.stop()
  }
}
