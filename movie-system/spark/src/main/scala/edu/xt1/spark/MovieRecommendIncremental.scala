package edu.xt1.spark

import org.apache.spark.ml.recommendation.ALS
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.{col, explode}

import java.nio.file.{Files, Paths}
import scala.collection.JavaConverters._
import SparkRecommendCommon.Rating

/**
 * 增量推荐：历史评分用预计算缓存，刷新时仅合并网站用户评分并重算网站用户推荐。
 */
object MovieRecommendIncremental {
  private case class Neighbor(movieId: String, sim: Double)

  private def loadContentIndex(path: String): Map[String, Seq[Neighbor]] = {
    val p = Paths.get(path.stripPrefix("file://"))
    if (!Files.exists(p)) return Map.empty
    Files.readAllLines(p).asScala.filter(_.trim.nonEmpty).map { line =>
      val mid = """"movieId"\s*:\s*"([^"]+)"""".r.findFirstMatchIn(line).map(_.group(1)).getOrElse("")
      val neighbors = """\["([^"]+)",([\d.Ee+-]+)\]""".r.findAllMatchIn(line).map { m =>
        Neighbor(m.group(1), m.group(2).toDouble)
      }.toSeq
      mid -> neighbors
    }.filter(_._1.nonEmpty).toMap
  }

  private def loadGraphxCache(path: String): (Map[String, Map[Long, Double]], Map[Long, Map[String, Double]]) = {
    val p = Paths.get(path.stripPrefix("file://"))
    if (!Files.exists(p)) return (Map.empty, Map.empty)

    val movieUsers = scala.collection.mutable.Map[String, Map[Long, Double]]()
    val userRatings = scala.collection.mutable.Map[Long, Map[String, Double]]()

    Files.readAllLines(p).asScala.filter(_.trim.nonEmpty).foreach { line =>
      if (line.contains("\"movieId\"")) {
        val mid = """"movieId"\s*:\s*"([^"]+)"""".r.findFirstMatchIn(line).map(_.group(1)).getOrElse("")
        val users = """\[(\d+),([\d.]+)\]""".r.findAllMatchIn(line).map { m =>
          m.group(1).toLong -> m.group(2).toDouble
        }.toMap
        if (mid.nonEmpty) movieUsers(mid) = users
      } else if (line.contains("\"userId\"")) {
        val uid = """"userId"\s*:\s*(\d+)""".r.findFirstMatchIn(line).map(_.group(1).toLong).getOrElse(-1L)
        val ratings = """\["([^"]+)",([\d.]+)\]""".r.findAllMatchIn(line).map { m =>
          m.group(1) -> m.group(2).toDouble
        }.toMap
        if (uid >= 0) userRatings(uid) = ratings
      }
    }
    (movieUsers.toMap, userRatings.toMap)
  }

  private def graphxForWebUsers(
    webRatings: Seq[Rating],
    movieUsers: Map[String, Map[Long, Double]],
    userRatings: Map[Long, Map[String, Double]],
    topN: Int,
  ): Seq[String] = {
    val ratingsByUser = userRatings.map { case (uid, rs) => uid -> rs.keySet }

    webRatings.groupBy(_.userId).flatMap { case (userId, userRatingList) =>
      val ratedMovies = userRatingList.map(_.movieId).toSet
      if (ratedMovies.isEmpty) Nil
      else {
        val neighborScores = scala.collection.mutable.Map[Long, Double]()
        ratedMovies.foreach { mid =>
          movieUsers.getOrElse(mid, Map.empty).foreach { case (otherUid, _) =>
            if (otherUid != userId) {
              val otherRated = ratingsByUser.getOrElse(otherUid, Set.empty)
              val common = ratedMovies.intersect(otherRated).size
              if (common > 0) {
                val sim = common.toDouble / math.sqrt(ratedMovies.size * otherRated.size)
                neighborScores(otherUid) = neighborScores.getOrElse(otherUid, 0.0) + sim
              }
            }
          }
        }

        val candidateScores = scala.collection.mutable.Map[String, Double]()
        neighborScores.foreach { case (neighborUid, sim) =>
          userRatings.getOrElse(neighborUid, Map.empty).foreach { case (movieId, rating) =>
            if (!ratedMovies.contains(movieId)) {
              candidateScores(movieId) = candidateScores.getOrElse(movieId, 0.0) + rating * sim
            }
          }
        }

        candidateScores.toSeq.sortBy(-_._2).take(topN).map { case (movieId, score) =>
          s"""{"userId":$userId,"movieId":"$movieId","score":$score}"""
        }
      }
    }.toSeq
  }

  private def contentForWebUsers(
    webRatings: Seq[Rating],
    index: Map[String, Seq[Neighbor]],
    topN: Int,
  ): Seq[String] = {
    webRatings.groupBy(_.userId).flatMap { case (userId, userRatingList) =>
      val ratedIds = userRatingList.map(_.movieId).toSet
      val aggregated = scala.collection.mutable.Map[String, Double]()

      userRatingList.foreach { r =>
        index.get(r.movieId).foreach { neighbors =>
          neighbors.foreach { nb =>
            if (!ratedIds.contains(nb.movieId) && nb.sim > 0.01) {
              aggregated(nb.movieId) = aggregated.getOrElse(nb.movieId, 0.0) + nb.sim * (r.rating / 10.0)
            }
          }
        }
      }

      aggregated.toSeq.sortBy(-_._2).take(topN).map { case (movieId, score) =>
        s"""{"userId":$userId,"movieId":"$movieId","score":$score}"""
      }
    }.toSeq
  }

  def main(args: Array[String]): Unit = {
    val historyPath = if (args.length > 0) args(0) else "data/ratings_history.ndjson"
    val webPath = if (args.length > 1) args(1) else "data/ratings_web.ndjson"
    val outputDir = if (args.length > 2) args(2) else "output"
    val webUserOffset = if (args.length > 3) args(3).toLong else 1000000L
    val contentIndexPath = if (args.length > 4) args(4) else s"$outputDir/content_similarity_index.ndjson"
    val graphxCachePath = if (args.length > 5) args(5) else s"$outputDir/graphx_history_cache.ndjson"
    val targetUserIdOpt = if (args.length > 6 && args(6).trim.nonEmpty) Some(args(6).toLong) else None

    val webRatingsAll = SparkRecommendCommon.readRatingsNdjson(webPath).filter(_.userId >= webUserOffset)
    val webRatings = targetUserIdOpt match {
      case Some(uid) => webRatingsAll.filter(_.userId == uid)
      case None => webRatingsAll
    }
    val targetUserIds = webRatings.map(_.userId).distinct.toSet

    if (targetUserIds.isEmpty) {
      println("No web user ratings to process.")
      return
    }

    println(s"Incremental recommend for ${targetUserIds.size} web user(s): ${targetUserIds.mkString(", ")}")

    val spark = SparkSession.builder()
      .appName("MovieRecommendIncremental")
      .master(sys.env.getOrElse("SPARK_MASTER", "local[*]"))
      .config("spark.hadoop.fs.defaultFS", "file:///")
      .getOrCreate()

    import spark.implicits._

    // ----- ALS: train on history + web, recommend subset only -----
    val historyUri = SparkLocalPaths.toUri(historyPath)
    val webUri = SparkLocalPaths.toUri(webPath)
    val historyDf = spark.read.json(historyUri).as[Rating]
    val webDf = spark.read.json(webUri).as[Rating]
    val ratings = historyDf.union(webDf).dropDuplicates(Seq("userId", "movieId"))
    val ratingCount = ratings.count()
    println(s"ALS training ratings: $ratingCount")

    val userIndex = ratings.select("userId").distinct()
      .rdd.zipWithIndex()
      .map { case (row, idx) => (row.getLong(0), idx.toInt) }
      .collect()
      .toMap

    val movieIndex = ratings.select("movieId").distinct()
      .rdd.zipWithIndex()
      .map { case (row, idx) => (row.getString(0), idx.toInt) }
      .collect()
      .toMap

    val indexedRatings = ratings.map { r =>
      (userIndex(r.userId), movieIndex(r.movieId), r.rating)
    }.toDF("userId", "movieId", "rating")

    val maxIter = sys.env.getOrElse("SPARK_ALS_MAX_ITER", "5").toInt
    val als = new ALS()
      .setMaxIter(maxIter)
      .setRegParam(0.1)
      .setRank(10)
      .setUserCol("userId")
      .setItemCol("movieId")
      .setRatingCol("rating")
      .setColdStartStrategy("drop")

    val model = als.fit(indexedRatings)

    val reverseUserIndex = spark.sparkContext.broadcast(userIndex.map { case (k, v) => v -> k })
    val reverseMovieIndex = spark.sparkContext.broadcast(movieIndex.map { case (k, v) => v -> k })

    val indexedTargetUsers = targetUserIds.flatMap(uid => userIndex.get(uid)).toSeq
    val alsItems: Seq[String] = if (indexedTargetUsers.nonEmpty) {
      val userSubsetDf = indexedTargetUsers.toDF("userId")
      val alsRecs = model.recommendForUserSubset(userSubsetDf, 10)
      alsRecs
        .select(col("userId"), explode(col("recommendations")).as("rec"))
        .select(
          col("userId").cast("int").as("userIdx"),
          col("rec.movieId").cast("int").as("movieIdx"),
          col("rec.rating").cast("double").as("score")
        )
        .collect()
        .flatMap { row =>
          val userIdx = row.getAs[Int]("userIdx")
          val movieIdx = row.getAs[Int]("movieIdx")
          val score = row.getAs[Double]("score")
          for {
            uid <- reverseUserIndex.value.get(userIdx)
            mid <- reverseMovieIndex.value.get(movieIdx)
          } yield s"""{"userId":$uid,"movieId":"$mid","score":$score}"""
        }
        .toSeq
    } else {
      println("WARN: target web users not found in ALS index")
      Seq.empty[String]
    }

    println(s"ALS items for web users: ${alsItems.size}")

    spark.stop()

    // ----- GraphX & Content: driver-side from caches -----
    val (movieUsers, userRatings) = loadGraphxCache(graphxCachePath)
    if (movieUsers.isEmpty) {
      println(s"WARN: GraphX cache missing at $graphxCachePath")
    }
    val graphxItems = graphxForWebUsers(webRatings, movieUsers, userRatings, 8)
    println(s"GraphX items for web users: ${graphxItems.size}")

    val contentIndex = loadContentIndex(contentIndexPath)
    if (contentIndex.isEmpty) {
      println(s"WARN: Content index missing at $contentIndexPath")
    }
    val contentItems = contentForWebUsers(webRatings, contentIndex, 10)
    println(s"Content items for web users: ${contentItems.size}")

    SparkRecommendCommon.mergeRecommendItems(
      s"$outputDir/recommendations_als.json",
      "als",
      alsItems,
      targetUserIds,
    )
    SparkRecommendCommon.mergeRecommendItems(
      s"$outputDir/recommendations_graphx.json",
      "graphx",
      graphxItems,
      targetUserIds,
    )
    SparkRecommendCommon.mergeRecommendItems(
      s"$outputDir/recommendations_content.json",
      "content",
      contentItems,
      targetUserIds,
    )

    println(s"Incremental recommendations merged into $outputDir")
  }
}
