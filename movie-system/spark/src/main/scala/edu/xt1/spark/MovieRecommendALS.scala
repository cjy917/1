package edu.xt1.spark

import org.apache.spark.ml.recommendation.ALS
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions.{col, explode}

/**
 * 基于 Spark MLlib ALS 的协同过滤电影推荐
 * 用户 ID、电影 ID 均映射为连续整数索引（Spark ALS 要求）
 */
object MovieRecommendALS {
  case class Rating(userId: Long, movieId: String, rating: Double)

  def main(args: Array[String]): Unit = {
    val ratingsPath = if (args.length > 0) args(0) else "data/ratings.json"
    val outputPath = if (args.length > 1) args(1) else "output/recommendations.json"

    val spark = SparkSession.builder()
      .appName("MovieRecommendALS")
      .master(sys.env.getOrElse("SPARK_MASTER", "local[*]"))
      .config("spark.hadoop.fs.defaultFS", "file:///")
      .getOrCreate()

    import spark.implicits._

    val ratingsUri = SparkLocalPaths.toUri(ratingsPath)
    // NDJSON：每行一个 JSON 对象；勿用 multiline=true（会把根级 JSON 数组当成 1 条记录）
    val ratings = spark.read.json(ratingsUri).as[Rating]
    val ratingCount = ratings.count()
    println(s"Loaded $ratingCount ratings")

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

    println(s"Users: ${userIndex.size}, Movies: ${movieIndex.size}")

    val indexedRatings = ratings.map { r =>
      (userIndex(r.userId), movieIndex(r.movieId), r.rating)
    }.toDF("userId", "movieId", "rating")

    val als = new ALS()
      .setMaxIter(10)
      .setRegParam(0.1)
      .setRank(10)
      .setUserCol("userId")
      .setItemCol("movieId")
      .setRatingCol("rating")
      .setColdStartStrategy("drop")

    val model = als.fit(indexedRatings)
    val recommendations = model.recommendForAllUsers(10)

    val reverseUserIndex = spark.sparkContext.broadcast(userIndex.map { case (k, v) => v -> k })
    val reverseMovieIndex = spark.sparkContext.broadcast(movieIndex.map { case (k, v) => v -> k })

    val result = recommendations
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
        } yield (uid, mid, score)
      }

    println(s"Generated ${result.size} recommendations for ${result.map(_._1).distinct.size} users")

    val payload = result.map { case (userId, movieId, score) =>
      s"""{"userId":$userId,"movieId":"$movieId","score":$score}"""
    }.mkString("[", ",", "]")

    import java.nio.file.{Files, Paths}
    Files.createDirectories(Paths.get(outputPath).getParent)
    val content = s"""{"algorithm":"als","items":$payload}""".getBytes("UTF-8")
    Files.write(Paths.get(outputPath), content)
    Files.write(Paths.get(outputPath).getParent.resolve("recommendations_als.json"), content)

    println(s"ALS recommendations saved to $outputPath (${result.size} items)")
    spark.stop()
  }
}
