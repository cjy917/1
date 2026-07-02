# 电影推荐系统 - 数据恢复指南

## 📋 文件清单

| 文件 | 大小 | 说明 |
|------|------|------|
| `films_data.tar.gz` | ~22 MB | 清洗后的数据文件 + 脚本 + 文档 |
| `movies_backup.sql` | ~21 MB | MySQL数据库备份 |

---

## 🔧 环境要求

### 基础环境
- Python 3.8+
- Java 8+（Spark需要）

### 可选环境
- MySQL 8.0+（用于数据库方式）
- Spark 3.4.0+（用于大数据处理）

---

## 🚀 快速开始

### 方式一：直接使用数据文件（推荐）

#### 1. 解压文件

**Windows：**
- 右键 `films_data.tar.gz` → 解压到 `films_data` 文件夹

**Linux：**
```bash
tar -xzvf films_data.tar.gz
```

#### 2. 使用Spark读取数据

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("MovieAnalysis").getOrCreate()

# 读取豆瓣数据
douban_df = spark.read.parquet("cleaned_data/douban/19_20_cleaned.parquet")

# 读取TMDb数据（以2015年为例）
tmdb_df = spark.read.parquet("cleaned_data/tmdb/2015_cleaned.parquet")

# 读取评分数据
ratings_df = spark.read.parquet("ratings/ratings.parquet")

# 查看数据
douban_df.show(5)
```

#### 3. 使用Pandas读取数据

```python
import pandas as pd

# 读取CSV文件
df = pd.read_csv("cleaned_data/douban/19_20_cleaned.csv/part-00000*.csv", encoding="utf-8")

# 查看数据
print(df.head())
```

---

### 方式二：恢复MySQL数据库

#### 1. 创建数据库

```bash
mysql -u root -p -e "CREATE DATABASE movies_db;"
```

#### 2. 导入数据

```bash
mysql -u root -p movies_db < movies_backup.sql
```

#### 3. 连接数据库

```python
import pymysql

conn = pymysql.connect(
    host="localhost",
    user="root",
    password="your_password",
    database="movies_db",
    charset="utf8mb4"
)

# 查询示例
with conn.cursor() as cursor:
    cursor.execute("SELECT title, rating FROM movies LIMIT 10")
    results = cursor.fetchall()
    for row in results:
        print(f"{row[0]}: {row[1]}分")

conn.close()
```

---

## 📁 目录结构

```
films_data/
├── cleaned_data/          # 清洗后的数据
│   ├── douban/            # 豆瓣数据
│   │   ├── 19_20_cleaned.csv/
│   │   └── 19_20_cleaned.parquet/
│   └── tmdb/              # TMDb数据
│       ├── 2015_cleaned.csv/
│       ├── 2015_cleaned.parquet/
│       ├── 2016_cleaned.csv/
│       ├── 2016_cleaned.parquet/
│       ├── 2017_cleaned.csv/
│       ├── 2017_cleaned.parquet/
│       ├── 2018_cleaned.csv/
│       ├── 2018_cleaned.parquet/
│       ├── 21_22_cleaned.csv/
│       ├── 21_22_cleaned.parquet/
│       ├── 23_24_cleaned.csv/
│       ├── 23_24_cleaned.parquet/
│       ├── 25_26_cleaned.csv/
│       └── 25_26_cleaned.parquet/
├── ratings/               # 评分数据
│   ├── ratings.csv/
│   └── ratings.parquet/
├── docs/                  # 文档
│   ├── data_dictionary.md     # 数据字典
│   └── handover_document.md   # 交接文档
└── scripts/               # 脚本
    ├── clean_movies.py        # 数据清洗脚本
    ├── extract_ratings.py     # 评分提取脚本
    ├── import_to_mysql.py     # MySQL导入脚本
    ├── import_to_neo4j.py     # Neo4j导入脚本
    └── movie_recommendation.py # 推荐算法示例
```

---

## 📊 数据说明

### 数据规模
- 总电影数：6766部（2015-2026年）
- 评分数据：约33830条

### 数据格式

| 字段名 | 说明 | 示例 |
|--------|------|------|
| movie_id | 电影ID | 123456 |
| title | 中文名称 | 肖申克的救赎 |
| rating | 评分（10分制） | 9.7 |
| rating_count | 评分人数 | 1000000 |
| release_date | 上映日期 | 1994-09-23 |
| directors | 导演（竖线分隔） | 弗兰克·德拉邦特 |
| genres | 类型（竖线分隔） | 剧情\|犯罪 |
| actors | 主演（竖线分隔） | 蒂姆·罗宾斯\|摩根·弗里曼 |
| reviews | 评论内容 | [评论1] 作者: xxx \| 评分: 9/10 ... |

### 评分数据字段

| 字段名 | 说明 |
|--------|------|
| user_id | 评论作者 |
| movie_id | 电影ID |
| rating | 用户评分（10分制） |
| comment | 评论内容 |

---

## 📖 使用示例

### 示例1：统计评分分布

```python
ratings_df = spark.read.parquet("ratings/ratings.parquet")
ratings_df.groupBy("rating").count().orderBy("rating").show()
```

### 示例2：查询高分电影

```python
movies_df = spark.read.parquet("cleaned_data/douban/19_20_cleaned.parquet")
movies_df.filter(movies_df.rating > 8).orderBy(movies_df.rating.desc()).show(10)
```

### 示例3：训练推荐模型

```python
from pyspark.ml.recommendation import ALS

ratings_df = spark.read.parquet("ratings/ratings.parquet")

als = ALS(
    rank=10,
    maxIter=10,
    userCol="user_id",
    itemCol="movie_id",
    ratingCol="rating",
    coldStartStrategy="drop"
)
model = als.fit(ratings_df)
```

---

## ❓ 常见问题

### Q1：解压后找不到CSV文件？
CSV文件在子目录中，例如：
```
cleaned_data/douban/19_20_cleaned.csv/part-00000-xxx.csv
```

### Q2：Spark读取失败？
确保Java环境已正确配置：
```bash
export JAVA_HOME=/path/to/java
export PATH=$JAVA_HOME/bin:$PATH
```

### Q3：MySQL导入失败？
检查MySQL版本是否支持utf8mb4字符集，确保内存足够。

### Q4：需要安装什么依赖？
```bash
pip install pyspark pandas pymysql
```

---

## 📝 参考文档

- `docs/data_dictionary.md` — 详细数据字典
- `docs/handover_document.md` — 完整交接文档