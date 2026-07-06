package edu.xt1.spark

import java.nio.file.{Files, Paths}

import scala.collection.JavaConverters._

/** 推荐任务共用的 JSON 读写与结果合并。 */
object SparkRecommendCommon {
  case class Rating(userId: Long, movieId: String, rating: Double)

  def readRatingsNdjson(path: String): Seq[Rating] = {
    val p = Paths.get(path.stripPrefix("file://"))
    if (!Files.exists(p)) return Seq.empty
    Files.readAllLines(p).asScala
      .filter(_.trim.nonEmpty)
      .map { line =>
        val uid = """"userId"\s*:\s*(\d+)""".r.findFirstMatchIn(line).map(_.group(1).toLong).getOrElse(-1L)
        val mid = """"movieId"\s*:\s*"([^"]+)"""".r.findFirstMatchIn(line).map(_.group(1)).getOrElse("")
        val score = """"rating"\s*:\s*([\d.]+)""".r.findFirstMatchIn(line).map(_.group(1).toDouble).getOrElse(0.0)
        Rating(uid, mid, score)
      }
      .filter(r => r.userId >= 0 && r.movieId.nonEmpty && r.rating > 0)
      .toSeq
  }

  def mergeRecommendItems(
    outputPath: String,
    algorithm: String,
    newItems: Seq[String],
    targetUserIds: Set[Long],
  ): Unit = {
    val path = Paths.get(outputPath)
    Files.createDirectories(path.getParent)

    val existingItems = if (Files.exists(path)) {
      val text = new String(Files.readAllBytes(path), "UTF-8")
      val itemsStart = text.indexOf("\"items\":[")
      if (itemsStart < 0) Seq.empty[String]
      else {
        val body = text.substring(itemsStart + 9)
        val end = body.lastIndexOf(']')
        if (end < 0) Seq.empty[String]
        else {
          body.substring(0, end).split("},").iterator.map { chunk =>
            val c = chunk.trim
            if (c.endsWith("}")) c else c + "}"
          }.filter(_.contains("\"userId\"")).toSeq
        }
      }
    } else Seq.empty[String]

    val kept = existingItems.filter { item =>
      val uid = """"userId"\s*:\s*(\d+)""".r.findFirstMatchIn(item).map(_.group(1).toLong)
      uid.forall(id => !targetUserIds.contains(id))
    }

    val merged = kept ++ newItems
    val payload = s"""{"algorithm":"$algorithm","items":[${merged.mkString(",")}]}"""
    Files.write(path, payload.getBytes("UTF-8"))
  }
}
