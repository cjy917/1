from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, when, trim, regexp_replace, split, concat_ws, lit
from pyspark.sql.types import StringType, IntegerType, FloatType
import subprocess
import os

def convert_to_simplified(text):
    if text is None:
        return None
    try:
        result = subprocess.run(
            ['opencc', '-c', 't2s.json'],
            input=text.encode('utf-8'),
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except Exception:
        return text

def main():
    spark = SparkSession.builder \
        .appName("MovieDataCleaning") \
        .getOrCreate()

    input_dir = "../../films_data/data"
    output_dir = "../../films_data/cleaned_data"
    
    os.makedirs(output_dir, exist_ok=True)

    chinese_to_english = {
        "豆瓣电影ID": "movie_id",
        "电影ID": "movie_id",
        "中文名称": "title",
        "评分": "rating",
        "评分总人数": "rating_count",
        "上映日期": "release_date",
        "上映年份": "release_year",
        "导演": "directors",
        "编剧": "writers",
        "主演": "actors",
        "电影别名": "aliases",
        "简介": "summary",
        "详情页链接": "detail_url",
        "影片语言": "languages",
        "影片类型": "genres",
        "片长": "duration",
        "评论内容": "reviews",
        "制片国家/地区": "countries",
        "获奖情况": "awards",
        "影评数": "review_count",
        "封面路径": "cover_path"
    }

    convert_to_simplified_udf = udf(convert_to_simplified, StringType())

    csv_files = [
        ("19_20.csv", "douban"),
        ("2015.csv", "tmdb"),
        ("2016.csv", "tmdb"),
        ("2017.csv", "tmdb"),
        ("2018.csv", "tmdb"),
        ("21_22.csv", "tmdb"),
        ("23_24.csv", "tmdb"),
        ("25_26.csv", "tmdb")
    ]

    for csv_file, source in csv_files:
        input_path = f"{input_dir}/{csv_file}"
        
        if not os.path.exists(input_path):
            print(f"文件不存在: {input_path}")
            continue

        df = spark.read.csv(
            f"file://{input_path}",
            header=True,
            encoding="utf-8",
            inferSchema=True,
            quote='"',
            escape='"',
            multiLine=True
        )

        for col_name in df.columns:
            if col_name in chinese_to_english:
                df = df.withColumnRenamed(col_name, chinese_to_english[col_name])

        df = df.filter(
            (col("movie_id").isNotNull()) & 
            (col("title").isNotNull()) & 
            (col("movie_id").rlike("^[0-9]+$"))
        )

        df = df \
            .withColumn("title", convert_to_simplified_udf(col("title"))) \
            .withColumn("aliases", convert_to_simplified_udf(col("aliases"))) \
            .withColumn("summary", convert_to_simplified_udf(col("summary"))) \
            .withColumn("reviews", convert_to_simplified_udf(col("reviews"))) \
            .withColumn("directors", convert_to_simplified_udf(col("directors"))) \
            .withColumn("writers", convert_to_simplified_udf(col("writers"))) \
            .withColumn("actors", convert_to_simplified_udf(col("actors")))

        df = df \
            .withColumn("reviews", regexp_replace(col("reviews"), "[\\r\\n]+", " ")) \
            .withColumn("summary", regexp_replace(col("summary"), "[\\r\\n]+", " "))

        def normalize_multi_value(df, col_name, source):
            if source == "tmdb":
                df = df.withColumn(col_name, regexp_replace(col(col_name), '"', ''))
                df = df.withColumn(col_name, regexp_replace(col(col_name), ',', '|'))
            df = df.withColumn(col_name, trim(regexp_replace(col(col_name), '[|]+', '|')))
            df = df.withColumn(col_name, regexp_replace(col(col_name), '^[|]|[|]$', ''))
            return df

        df = normalize_multi_value(df, "directors", source)
        df = normalize_multi_value(df, "writers", source)
        df = normalize_multi_value(df, "actors", source)
        df = normalize_multi_value(df, "languages", source)
        df = normalize_multi_value(df, "genres", source)
        df = normalize_multi_value(df, "countries", source)
        df = normalize_multi_value(df, "aliases", source)

        df = df \
            .withColumn("rating", when(col("rating").isNull(), lit(0.0)).otherwise(col("rating").cast(FloatType()))) \
            .withColumn("rating_count", when(col("rating_count").isNull(), lit(0)).otherwise(col("rating_count").cast(IntegerType()))) \
            .withColumn("review_count", when(col("review_count").isNull(), lit(0)).otherwise(col("review_count").cast(IntegerType()))) \
            .withColumn("release_year", when(col("release_year").isNull(), lit(0)).otherwise(col("release_year").cast(IntegerType()))) \
            .withColumn("aliases", when(col("aliases").isNull() | (trim(col("aliases")) == ""), lit("未知")).otherwise(col("aliases"))) \
            .withColumn("awards", when(col("awards").isNull() | (trim(col("awards")) == ""), lit("无")).otherwise(col("awards"))) \
            .withColumn("cover_path", when(col("cover_path").isNull() | (trim(col("cover_path")) == ""), lit("")).otherwise(col("cover_path")))

        df = df.withColumn("cover_path", concat_ws("", lit("./picture/"), col("cover_path")))

        output_csv_path = f"{output_dir}/{source}/{csv_file.replace('.csv', '_cleaned.csv')}"
        output_parquet_path = f"{output_dir}/{source}/{csv_file.replace('.csv', '_cleaned.parquet')}"
        
        os.makedirs(f"{output_dir}/{source}", exist_ok=True)

        df.write \
            .option("header", "true") \
            .option("encoding", "utf-8") \
            .csv(f"file://{output_csv_path}", mode="overwrite")

        df.write \
            .parquet(f"file://{output_parquet_path}", mode="overwrite")

        print(f"清洗完成: {csv_file} -> {output_csv_path}")
        print(f"记录数: {df.count()}")

    spark.stop()

if __name__ == "__main__":
    main()