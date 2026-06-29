from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, explode, lit
from pyspark.sql.types import StringType, FloatType, StructType, StructField, ArrayType
import re

def extract_reviews(reviews_str):
    if reviews_str is None:
        return []
    reviews = []
    parts = reviews_str.split('[评论')
    for part in parts[1:]:
        idx_end = part.find(']')
        if idx_end == -1:
            continue
        idx = int(part[:idx_end])
        content = part[idx_end+1:].strip()
        author_match = re.search(r'作者:\s*([^|]+)', content)
        rating_match = re.search(r'评分:\s*([\d.]+)/10', content)
        comment_match = re.search(r'([^\n]+)$', content)
        
        author = author_match.group(1).strip() if author_match else "unknown"
        rating = float(rating_match.group(1)) if rating_match else 0.0
        comment = comment_match.group(1).strip() if comment_match else ""
        
        reviews.append((author, rating, comment))
    return reviews

def main():
    spark = SparkSession.builder \
        .appName("ExtractRatings") \
        .getOrCreate()

    hdfs_path = "hdfs://Master:9000/films/cleaned_data"
    output_path_hdfs = "hdfs://Master:9000/films/ratings"
    output_path_local = "/home/zsy/films/ratings"

    extract_reviews_udf = udf(extract_reviews, ArrayType(StructType([
        StructField("author", StringType()),
        StructField("rating", FloatType()),
        StructField("comment", StringType())
    ])))

    csv_files = [
        ("19_20_cleaned.parquet", "douban"),
        ("2015_cleaned.parquet", "tmdb"),
        ("2016_cleaned.parquet", "tmdb"),
        ("2017_cleaned.parquet", "tmdb"),
        ("2018_cleaned.parquet", "tmdb"),
        ("21_22_cleaned.parquet", "tmdb"),
        ("23_24_cleaned.parquet", "tmdb"),
        ("25_26_cleaned.parquet", "tmdb")
    ]

    all_ratings_df = None

    for parquet_file, source in csv_files:
        try:
            input_path = f"{hdfs_path}/{source}/{parquet_file}"
            df = spark.read.parquet(input_path)
            
            ratings_df = df.select(
                col("movie_id"),
                col("title"),
                explode(extract_reviews_udf(col("reviews"))).alias("review")
            ).select(
                col("movie_id"),
                col("title"),
                col("review.author").alias("user_id"),
                col("review.rating").alias("rating"),
                col("review.comment").alias("comment"),
                lit(source).alias("source")
            ).filter(col("rating") > 0)
            
            if all_ratings_df is None:
                all_ratings_df = ratings_df
            else:
                all_ratings_df = all_ratings_df.union(ratings_df)
            
            print(f"从 {parquet_file} 提取了 {ratings_df.count()} 条评分")
        
        except Exception as e:
            print(f"处理 {parquet_file} 失败: {e}")

    if all_ratings_df is None:
        print("没有提取到任何评分数据")
        spark.stop()
        return

    print(f"\n=== 评分数据统计 ===")
    print(f"总评分条数: {all_ratings_df.count()}")
    print(f"总用户数: {all_ratings_df.select('user_id').distinct().count()}")
    print(f"总电影数: {all_ratings_df.select('movie_id').distinct().count()}")
    avg_rating = all_ratings_df.select('rating').agg({'rating': 'avg'}).collect()[0][0]
    print(f"平均评分: {avg_rating:.2f}")

    print(f"\n按数据源分布:")
    all_ratings_df.groupBy("source").count().show()

    print(f"\n按评分分布:")
    rating_dist_df = all_ratings_df.groupBy("rating").count().orderBy("rating")
    rating_dist_df.show()

    all_ratings_df.write \
        .option("header", "true") \
        .option("encoding", "utf-8") \
        .csv(f"{output_path_hdfs}/ratings.csv", mode="overwrite")

    all_ratings_df.write \
        .parquet(f"{output_path_hdfs}/ratings.parquet", mode="overwrite")

    print(f"\n评分数据已保存到 HDFS: {output_path_hdfs}")

    local_ratings_df = all_ratings_df.coalesce(1)
    
    local_ratings_df.write \
        .option("header", "true") \
        .option("encoding", "utf-8") \
        .csv(f"file://{output_path_local}/ratings.csv", mode="overwrite")

    local_ratings_df.write \
        .parquet(f"file://{output_path_local}/ratings.parquet", mode="overwrite")

    print(f"评分数据已保存到本地: {output_path_local}")

    user_activity_df = all_ratings_df.groupBy("user_id").count()
    top_users = user_activity_df.orderBy(col("count").desc()).limit(10)
    print(f"\n最活跃的10个用户:")
    top_users.show()

    movie_rating_count_df = all_ratings_df.groupBy("movie_id", "title").count()
    top_movies = movie_rating_count_df.orderBy(col("count").desc()).limit(10)
    print(f"\n评分最多的10部电影:")
    top_movies.show()

    spark.stop()

if __name__ == "__main__":
    main()