package edu.xt1.spark

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._

/**
 * Spark SQL 电影数据分析
 * 运行: spark-submit --class edu.xt1.spark.MovieDataAnalysis target/movie-recommend-spark-1.0.0.jar <movies.csv> <output_dir>
 */
object MovieDataAnalysis {
  def main(args: Array[String]): Unit = {
    val moviesPath = if (args.length > 0) args(0) else "../merged/movies.csv"
    val outputDir = if (args.length > 1) args(1) else "output/analysis"

    val spark = SparkSession.builder()
      .appName("MovieDataAnalysis")
      .master(sys.env.getOrElse("SPARK_MASTER", "local[*]"))
      .getOrCreate()

    import spark.implicits._

    val movies = spark.read
      .option("header", "true")
      .option("encoding", "UTF-8")
      .csv(moviesPath)
      .withColumnRenamed("电影ID", "movie_id")
      .withColumnRenamed("中文名称", "title")
      .withColumnRenamed("评分", "rating")
      .withColumnRenamed("上映年份", "release_year")
      .withColumnRenamed("影片类型", "genres")
      .withColumnRenamed("制片国家/地区", "country")
      .withColumn("rating", col("rating").cast("double"))
      .withColumn("release_year", col("release_year").cast("int"))

    movies.createOrReplaceTempView("movies")

    val genreStats = movies
      .select(explode(split(col("genres"), ",")).as("genre"))
      .groupBy(trim(col("genre")).as("genre"))
      .count()
      .orderBy(desc("count"))

    val yearStats = movies
      .filter(col("release_year").isNotNull)
      .groupBy("release_year")
      .count()
      .orderBy("release_year")

    val countryStats = movies
      .filter(col("country").isNotNull && col("country") =!= "")
      .groupBy("country")
      .count()
      .orderBy(desc("count"))

    val ratingStats = movies
      .filter(col("rating").isNotNull)
      .agg(
        avg("rating").as("avg_rating"),
        min("rating").as("min_rating"),
        max("rating").as("max_rating"),
        count("*").as("total_movies")
      )

    genreStats.coalesce(1).write.mode("overwrite").json(s"$outputDir/genres")
    yearStats.coalesce(1).write.mode("overwrite").json(s"$outputDir/years")
    countryStats.coalesce(1).write.mode("overwrite").json(s"$outputDir/countries")
    ratingStats.coalesce(1).write.mode("overwrite").json(s"$outputDir/summary")

    println(s"Analysis finished. Output: $outputDir")
    spark.stop()
  }
}
