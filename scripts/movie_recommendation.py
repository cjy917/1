from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, explode, regexp_extract, split, monotonically_increasing_id
from pyspark.sql.types import StringType, FloatType, IntegerType, StructType, StructField, ArrayType
from pyspark.ml.recommendation import ALS, ALSModel
from pyspark.ml.feature import StringIndexer
from pyspark.mllib.recommendation import Rating
from pyspark.graphx import Graph, VertexId
from pyspark.mllib.linalg import Vectors
from pyspark.mllib.clustering import KMeans
import os

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
        author_match = __import__('re').search(r'作者:\s*([^|]+)', content)
        rating_match = __import__('re').search(r'评分:\s*([\d.]+)/10', content)
        comment_match = __import__('re').search(r'([^\n]+)$', content)
        
        author = author_match.group(1).strip() if author_match else "unknown"
        rating = float(rating_match.group(1)) if rating_match else 0.0
        comment = comment_match.group(1).strip() if comment_match else ""
        
        reviews.append((author, rating, comment))
    return reviews

def main():
    spark = SparkSession.builder \
        .appName("MovieRecommendation") \
        .getOrCreate()

    hdfs_path = "hdfs://Master:9000/films/cleaned_data"
    
    douban_df = spark.read.parquet(f"{hdfs_path}/douban/19_20_cleaned.parquet")
    tmdb_dfs = []
    for year in ["2015", "2016", "2017", "2018", "21_22", "23_24", "25_26"]:
        try:
            df = spark.read.parquet(f"{hdfs_path}/tmdb/{year}_cleaned.parquet")
            tmdb_dfs.append(df)
        except Exception:
            pass
    
    all_movies_df = douban_df
    for df in tmdb_dfs:
        all_movies_df = all_movies_df.union(df)

    extract_reviews_udf = udf(extract_reviews, ArrayType(StructType([
        StructField("author", StringType()),
        StructField("rating", FloatType()),
        StructField("comment", StringType())
    ])))

    movie_reviews_df = all_movies_df.select(
        col("movie_id"),
        col("title"),
        explode(extract_reviews_udf(col("reviews"))).alias("review")
    ).select(
        col("movie_id"),
        col("title"),
        col("review.author").alias("user_id"),
        col("review.rating").alias("rating")
    ).filter(col("rating") > 0)

    user_indexer = StringIndexer(inputCol="user_id", outputCol="user_idx")
    movie_indexer = StringIndexer(inputCol="movie_id", outputCol="movie_idx")
    
    user_model = user_indexer.fit(movie_reviews_df)
    movie_model = movie_indexer.fit(movie_reviews_df)
    
    indexed_df = user_model.transform(movie_reviews_df)
    indexed_df = movie_model.transform(indexed_df)
    
    indexed_df = indexed_df.withColumn("user_idx", col("user_idx").cast(IntegerType()))
    indexed_df = indexed_df.withColumn("movie_idx", col("movie_idx").cast(IntegerType()))
    indexed_df = indexed_df.withColumn("rating", col("rating").cast(FloatType()))

    als = ALS(
        rank=10,
        maxIter=10,
        regParam=0.1,
        userCol="user_idx",
        itemCol="movie_idx",
        ratingCol="rating",
        coldStartStrategy="drop"
    )
    
    model = als.fit(indexed_df)

    user_recs = model.recommendForAllUsers(10)
    movie_recs = model.recommendForAllItems(10)

    user_recs.show(5)
    movie_recs.show(5)

    predictions = model.transform(indexed_df)
    predictions.select("user_idx", "movie_idx", "rating", "prediction").show(10)

    output_dir = "hdfs://Master:9000/films/recommendations"
    user_recs.write.mode("overwrite").parquet(f"{output_dir}/user_recommendations")
    movie_recs.write.mode("overwrite").parquet(f"{output_dir}/movie_recommendations")
    predictions.write.mode("overwrite").parquet(f"{output_dir}/predictions")

    print("ALS recommendation completed!")

    # GraphX recommendation
    ratings_rdd = indexed_df.select("user_idx", "movie_idx", "rating") \
        .rdd.map(lambda x: ((x[0], x[1]), x[2]))
    
    user_vertices = indexed_df.select("user_idx").distinct() \
        .rdd.map(lambda x: (int(x[0]), ("user",)))
    
    movie_vertices = indexed_df.select("movie_idx").distinct() \
        .rdd.map(lambda x: (int(x[0]) + 1000000, ("movie",)))
    
    edges = ratings_rdd.map(lambda x: (int(x[0][0]), int(x[0][1]) + 1000000, x[1]))
    
    graph = Graph(user_vertices.union(movie_vertices), edges)
    
    print(f"Graph vertices: {graph.vertices.count()}")
    print(f"Graph edges: {graph.edges.count()}")
    
    degrees = graph.degrees.collect()
    print(f"Top 10 nodes by degree: {sorted(degrees, key=lambda x: x[1], reverse=True)[:10]}")

    connected_components = graph.connectedComponents().vertices.collect()
    print(f"Number of connected components: {len(set([v[1] for v in connected_components]))}")

    print("GraphX analysis completed!")

    spark.stop()

if __name__ == "__main__":
    main()