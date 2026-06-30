from pyspark.sql import SparkSession
from pyspark.sql.functions import lit, regexp_replace, substring, col
import subprocess
import os
import sys

def main():
    if len(sys.argv) < 2:
        print("用法: spark-submit --jars /path/to/mysql-connector-java.jar import_to_mysql.py <mysql_password>")
        sys.exit(1)
    
    mysql_password = sys.argv[1]
    
    spark = SparkSession.builder \
        .appName("ImportToMySQL") \
        .getOrCreate()

    local_path = "../../films_data/cleaned_data"
    mysql_url = "jdbc:mysql://localhost:3306/movies_db?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai"
    mysql_user = "root"

    create_db_cmd = f"mysql -u{mysql_user} -p{mysql_password} -e \"CREATE DATABASE IF NOT EXISTS movies_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;\""
    subprocess.run(create_db_cmd, shell=True, check=True)

    drop_table_cmd = f"mysql -u{mysql_user} -p{mysql_password} movies_db -e \"DROP TABLE IF EXISTS movies;\""
    subprocess.run(drop_table_cmd, shell=True, check=True)

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS movies (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        movie_id BIGINT NOT NULL,
        title VARCHAR(200) NOT NULL,
        rating FLOAT DEFAULT 0.0,
        rating_count INT DEFAULT 0,
        release_date VARCHAR(50),
        release_year INT DEFAULT 0,
        directors VARCHAR(1000),
        writers VARCHAR(1000),
        actors VARCHAR(2000),
        aliases VARCHAR(2000),
        summary TEXT,
        detail_url VARCHAR(500),
        languages VARCHAR(500),
        genres VARCHAR(500),
        duration VARCHAR(50),
        reviews TEXT,
        countries VARCHAR(500),
        awards VARCHAR(2000),
        review_count INT DEFAULT 0,
        cover_path VARCHAR(200),
        source VARCHAR(20),
        UNIQUE KEY uk_movie_id (movie_id, source)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """

    create_table_cmd = f"mysql -u{mysql_user} -p{mysql_password} movies_db -e \"{create_table_sql}\""
    subprocess.run(create_table_cmd, shell=True, check=True)

    jdbc_properties = {
        "user": mysql_user,
        "password": mysql_password,
        "driver": "com.mysql.cj.jdbc.Driver"
    }

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

    table_columns = [
        "movie_id", "title", "rating", "rating_count", "release_date", 
        "release_year", "directors", "writers", "actors", "aliases", 
        "summary", "detail_url", "languages", "genres", "duration", 
        "reviews", "countries", "awards", "review_count", "cover_path", "source"
    ]

    for parquet_file, source in csv_files:
        try:
            input_path = f"file://{local_path}/{source}/{parquet_file}"
            df = spark.read.parquet(input_path)
            
            original_count = df.count()
            
            df = df.withColumn("source", lit(source))
            
            df = df.filter(
                (df["movie_id"].isNotNull()) & 
                (df["title"].isNotNull()) & 
                (df["movie_id"].rlike("^[0-9]+$"))
            )
            
            df = df \
                .withColumn("aliases", substring(col("aliases"), 1, 1999)) \
                .withColumn("awards", substring(col("awards"), 1, 1999))
            
            filtered_count = df.count()
            removed_count = original_count - filtered_count
            
            df = df.select(table_columns)
            
            df.write \
                .mode("append") \
                .jdbc(url=mysql_url, table="movies", properties=jdbc_properties)
            
            print(f"成功导入 {parquet_file}，原始 {original_count} 条，过滤后 {filtered_count} 条（移除 {removed_count} 条无效数据）")
        except Exception as e:
            print(f"导入 {parquet_file} 失败: {e}")

    verify_cmd = f"mysql -u{mysql_user} -p{mysql_password} movies_db -e \"SELECT COUNT(*) as total_records, COUNT(DISTINCT source) as sources FROM movies;\""
    subprocess.run(verify_cmd, shell=True, check=True)

    spark.stop()

if __name__ == "__main__":
    main()