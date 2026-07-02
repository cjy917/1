package edu.xt1.spark

import org.apache.spark.graphx._
import org.apache.spark.rdd.RDD
import org.apache.spark.sql.SparkSession

/**
 * 基于 Spark GraphX 的图协同推荐
 * 构建用户-电影二部图，通过共同评分用户传播偏好（2-hop 图协同）
 */
object MovieRecommendGraphX {
  case class Rating(userId: Long, movieId: String, rating: Double)

  def main(args: Array[String]): Unit = {
    val ratingsPath = if (args.length > 0) args(0) else "data/ratings.json"
    val outputPath = if (args.length > 1) args(1) else "output/recommendations_graphx.json"
    val topN = if (args.length > 2) args(2).toInt else 8

    val spark = SparkSession.builder()
      .appName("MovieRecommendGraphX")
      .master(sys.env.getOrElse("SPARK_MASTER", "local[*]"))
      .config("spark.hadoop.fs.defaultFS", "file:///")
      .getOrCreate()

    import spark.implicits._

    val ratingsUri = SparkLocalPaths.toUri(ratingsPath)
    val ratings = spark.read.json(ratingsUri).as[Rating].collect()
    val movieIds = ratings.map(_.movieId).distinct.sorted
    val movieIdToLong = movieIds.zipWithIndex.map { case (id, idx) => id -> (idx + 1000000L) }.toMap
    val userIds = ratings.map(_.userId).distinct.sorted

    val edges: RDD[Edge[Double]] = spark.sparkContext.parallelize(
      ratings.map(r => Edge(r.userId.toLong, movieIdToLong(r.movieId), r.rating))
    )

    val graph = Graph.fromEdges(edges, 1.0).partitionBy(PartitionStrategy.EdgePartition2D)
    println(s"Graph: ${graph.vertices.count()} vertices, ${graph.edges.count()} edges")

    val ratingsByUser = ratings.groupBy(_.userId)

    val userRated = ratingsByUser.map { case (uid, rs) =>
      uid -> rs.map(_.movieId).toSet
    }

    val movieUsers = ratings.groupBy(_.movieId).map { case (mid, rs) =>
      mid -> rs.map(r => (r.userId, r.rating)).toMap
    }

    val recommendations = userIds.flatMap { userId =>
      val ratedMovies = userRated.getOrElse(userId, Set.empty)
      if (ratedMovies.isEmpty) {
        Nil
      } else {
        val neighborScores = scala.collection.mutable.Map[Long, Double]()
        ratedMovies.foreach { mid =>
          movieUsers.getOrElse(mid, Map.empty).foreach { case (otherUid, _) =>
            if (otherUid != userId) {
              val otherRated = userRated.getOrElse(otherUid, Set.empty)
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
          ratingsByUser.getOrElse(neighborUid, Array.empty[Rating]).foreach { r =>
            if (!ratedMovies.contains(r.movieId)) {
              candidateScores(r.movieId) = candidateScores.getOrElse(r.movieId, 0.0) + r.rating * sim
            }
          }
        }

        candidateScores.toSeq.sortBy(-_._2).take(topN).map { case (movieId, score) =>
          s"""{"userId":$userId,"movieId":"$movieId","score":$score}"""
        }
      }
    }

    import java.nio.file.{Files, Paths}
    Files.createDirectories(Paths.get(outputPath).getParent)
    Files.write(
      Paths.get(outputPath),
      s"""{"algorithm":"graphx","items":[${recommendations.mkString(",")}]}""".getBytes("UTF-8")
    )

    println(s"GraphX recommendations saved to $outputPath (${recommendations.size} items)")
    spark.stop()
  }
}
