package edu.xt1.spark

import java.io.File

/** 将本地路径转为 file:// URI，避免 Spark 误连 HDFS (localhost:9000)。 */
object SparkLocalPaths {
  def toUri(path: String): String = {
    if (path.startsWith("file:") || path.startsWith("hdfs:")) path
    else if (path.startsWith("/")) s"file://$path"
    else s"file://${new File(path).getAbsolutePath}"
  }
}
