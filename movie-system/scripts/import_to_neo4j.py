from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, explode, lit
from pyspark.sql.types import StringType, FloatType, StructType, StructField, ArrayType
from py2neo import Graph, Node
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
        .appName("ImportToNeo4j") \
        .getOrCreate()

    local_path = "/home/zsy/films/cleaned_data"
    neo4j_url = "bolt://localhost:7687"

    graph = Graph(neo4j_url)
    
    graph.run("MATCH (n) DETACH DELETE n")
    print("已清空现有数据")

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

    total_movies = 0
    total_users = 0
    total_ratings = 0

    for parquet_file, source in csv_files:
        try:
            input_path = f"file://{local_path}/{source}/{parquet_file}"
            df = spark.read.parquet(input_path)
            
            movie_reviews_df = df.select(
                col("movie_id"),
                col("title"),
                col("rating").alias("movie_rating"),
                col("rating_count"),
                col("genres"),
                col("directors"),
                col("release_year"),
                explode(extract_reviews_udf(col("reviews"))).alias("review")
            ).select(
                col("movie_id"),
                col("title"),
                col("movie_rating"),
                col("rating_count"),
                col("genres"),
                col("directors"),
                col("release_year"),
                col("review.author").alias("user_id"),
                col("review.rating").alias("rating"),
                col("review.comment").alias("comment")
            ).filter(col("rating") > 0)

            movie_list = movie_reviews_df.select(
                "movie_id", "title", "movie_rating", "rating_count", "genres", "directors", "release_year"
            ).distinct().collect()

            tx = graph.begin()
            for row in movie_list:
                movie_node = Node(
                    "Movie",
                    movie_id=str(row["movie_id"]),
                    title=row["title"],
                    rating=float(row["movie_rating"]) if row["movie_rating"] else 0.0,
                    rating_count=int(row["rating_count"]) if row["rating_count"] else 0,
                    genres=row["genres"] if row["genres"] else "",
                    directors=row["directors"] if row["directors"] else "",
                    release_year=int(row["release_year"]) if row["release_year"] else 0,
                    source=source
                )
                tx.create(movie_node)
            tx.commit()

            total_movies += len(movie_list)
            print(f"已创建 {len(movie_list)} 个电影节点")

            rating_list = movie_reviews_df.select(
                "movie_id", "user_id", "rating", "comment"
            ).collect()

            tx = graph.begin()
            for row in rating_list:
                tx.run(
                    """
                    MATCH (m:Movie {movie_id: $movie_id})
                    MERGE (u:User {user_id: $user_id})
                    MERGE (u)-[:RATED {score: $score, comment: $comment}]->(m)
                    """,
                    movie_id=str(row["movie_id"]),
                    user_id=row["user_id"],
                    score=float(row["rating"]),
                    comment=row["comment"]
                )
            tx.commit()

            total_ratings += len(rating_list)
            print(f"已创建 {len(rating_list)} 条评分关系")

        except Exception as e:
            print(f"导入 {parquet_file} 失败: {e}")

    user_count = graph.run("MATCH (u:User) RETURN COUNT(u)").evaluate()
    movie_count = graph.run("MATCH (m:Movie) RETURN COUNT(m)").evaluate()
    rating_count = graph.run("MATCH ()-[:RATED]->() RETURN COUNT(*)").evaluate()

    print(f"\n=== 导入结果 ===")
    print(f"电影节点数: {movie_count}")
    print(f"用户节点数: {user_count}")
    print(f"评分关系数: {rating_count}")

    if rating_count and rating_count > 0:
        avg_rating = graph.run("MATCH ()-[r:RATED]->() RETURN AVG(r.score)").evaluate()
        print(f"\n=== 图统计 ===")
        print(f"平均评分: {avg_rating:.2f}")

        top_movies = graph.run("""
            MATCH (m:Movie)
            RETURN m.title, m.rating, m.rating_count
            ORDER BY m.rating_count DESC
            LIMIT 5
        """).data()
        print("\n最热门的5部电影:")
        for movie in top_movies:
            print(f"  {movie['m.title']} - 评分: {movie['m.rating']}, 评分人数: {movie['m.rating_count']}")

    spark.stop()

if __name__ == "__main__":
    main()