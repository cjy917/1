"""
Spark MLlib ALS 电影推荐 - 集群版示例
运行环境：Linux + Hadoop + Spark 3.4+
"""
from pyspark.ml.recommendation import ALS
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("MovieRecommendALS").getOrCreate()

ratings_df = spark.read.parquet("hdfs://Master:9000/films/ratings/ratings.parquet")

als = ALS(
    rank=10,
    maxIter=10,
    regParam=0.1,
    userCol="user_id",
    itemCol="movie_id",
    ratingCol="rating",
    coldStartStrategy="drop",
)
model = als.fit(ratings_df)

recommendations = model.recommendForAllUsers(10)
recommendations.write.mode("overwrite").parquet("hdfs://Master:9000/films/output/als_recommendations")

print("Spark MLlib ALS 推荐完成")
