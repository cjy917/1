# 电影推荐系统 - 数据字典

## 一、数据概述

本数据集包含2015-2026年间上映的6766部电影数据，来源于豆瓣和TMDb两个平台。数据经过标准化清洗处理，统一采用英文字段名，适合后续推荐算法分析。

## 二、数据源说明

| 数据源 | 文件 | 年份范围 | 电影数量 | 特点 |
|--------|------|----------|----------|------|
| 豆瓣 | 19_20_cleaned.parquet | 2019-2020 | 1535 | 中文数据为主，包含详细短评 |
| TMDb | 2015_cleaned.parquet | 2015 | - | 英文数据为主 |
| TMDb | 2016_cleaned.parquet | 2016 | - | 英文数据为主 |
| TMDb | 2017_cleaned.parquet | 2017 | - | 英文数据为主 |
| TMDb | 2018_cleaned.parquet | 2018 | - | 英文数据为主 |
| TMDb | 21_22_cleaned.parquet | 2021-2022 | - | 英文数据为主 |
| TMDb | 23_24_cleaned.parquet | 2023-2024 | - | 英文数据为主 |
| TMDb | 25_26_cleaned.parquet | 2025-2026 | - | 英文数据为主 |

## 三、字段说明

### 基本信息字段

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| movie_id | BIGINT | 电影唯一标识符（豆瓣ID或TMDb ID） | 26266893 |
| title | STRING | 电影中文名称（已转换为简体） | 流浪地球 |
| rating | FLOAT | 电影评分（10分制） | 7.9 |
| rating_count | INT | 评分总人数 | 2049592 |
| release_date | STRING | 上映日期 | 2019-02-05(中国大陆) |
| release_year | INT | 上映年份 | 2019 |

### 人员信息字段

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| directors | STRING | 导演列表，竖线分隔 | 郭帆 |
| writers | STRING | 编剧列表，竖线分隔 | 龚格尔\|严东旭\|郭帆 |
| actors | STRING | 主演列表，竖线分隔 | 吴京\|屈楚萧\|李光洁 |

### 内容描述字段

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| aliases | STRING | 电影别名，竖线分隔（空值填充"未知"） | The Wandering Earth |
| summary | STRING | 剧情简介（已转换为简体） | 近未来，科学家们发现太阳急速衰老膨胀... |
| detail_url | STRING | 详情页链接 | https://movie.douban.com/subject/26266893/ |

### 分类信息字段

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| languages | STRING | 影片语言，竖线分隔 | 汉语普通话\|英语\|俄语 |
| genres | STRING | 影片类型，竖线分隔 | 科幻\|冒险\|灾难 |
| duration | STRING | 片长 | 125分钟 |
| countries | STRING | 制片国家/地区，竖线分隔 | 中国大陆\|中国香港 |

### 评价数据字段

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| reviews | STRING | 5条短评，每条包含作者、评分、内容 | [评论1] 作者: 张小北 \| 评分: 10/10（五颗星）... |
| awards | STRING | 获奖情况（空值填充"无"） | 第32届中国电影金鸡奖最佳故事片 |
| review_count | INT | 影评数 | 15000 |

### 文件路径字段

| 字段名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| cover_path | STRING | 封面图片路径（空值保持为空） | ./picture/p2933198755.webp |

## 四、多值字段处理规则

以下字段可能包含多个值，使用竖线（\|）作为分隔符：

- directors（导演）
- writers（编剧）
- actors（主演）
- aliases（别名）
- languages（语言）
- genres（类型）
- countries（国家/地区）

**解析示例：**

```python
# 解析导演字段
directors = row["directors"].split("|")
# ["郭帆", "龚格尔"]
```

## 五、评分格式说明

### 电影评分（rating字段）

- 豆瓣：原始为五星制，已转换为10分制
- TMDb：原始为10分制，保持不变
- 范围：0-10

### 评论评分（reviews字段）

每条评论的评分格式：
```
[评论N] 作者: XXX | 评分: X/10（X颗星）
评论内容...
```

**评分转换规则：**

| 豆瓣星级 | 10分制显示 |
|---------|-----------|
| 1星 | 2/10（一颗星） |
| 2星 | 4/10（两颗星） |
| 3星 | 6/10（三颗星） |
| 4星 | 8/10（四颗星） |
| 5星 | 10/10（五颗星） |

## 六、空值处理规则

| 字段类型 | 处理方式 | 说明 |
|---------|---------|------|
| 核心字段（rating, rating_count, release_year） | 填充0 | 便于数值计算 |
| 辅助字段（aliases） | 填充"未知" | 明确表示缺失 |
| 辅助字段（awards） | 填充"无" | 明确表示无获奖记录 |
| 辅助字段（cover_path） | 保持为空 | 表示封面下载失败 |

## 七、数据存储位置

### HDFS路径

```
hdfs://Master:9000/films/cleaned_data/
├── douban/
│   └── 19_20_cleaned.parquet/
└── tmdb/
    ├── 2015_cleaned.parquet/
    ├── 2016_cleaned.parquet/
    ├── 2017_cleaned.parquet/
    ├── 2018_cleaned.parquet/
    ├── 21_22_cleaned.parquet/
    ├── 23_24_cleaned.parquet/
    └── 25_26_cleaned.parquet/
```

### 本地路径（备份）

```
/home/zsy/films/cleaned_data/
├── douban/
│   ├── 19_20_cleaned.csv
│   └── 19_20_cleaned.parquet/
└── tmdb/
    ├── 2015_cleaned.csv
    ├── 2015_cleaned.parquet/
    └── ...（其他年份）
```

## 八、数据读取方式

### Spark 读取（推荐）

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("MovieAnalysis").getOrCreate()

# 读取豆瓣数据
douban_df = spark.read.parquet("hdfs://Master:9000/films/cleaned_data/douban/19_20_cleaned.parquet")

# 读取所有TMDb数据
from functools import reduce
tmdb_dfs = []
for year in ["2015", "2016", "2017", "2018", "21_22", "23_24", "25_26"]:
    df = spark.read.parquet(f"hdfs://Master:9000/films/cleaned_data/tmdb/{year}_cleaned.parquet")
    tmdb_dfs.append(df)

all_tmdb_df = reduce(lambda a, b: a.union(b), tmdb_dfs)

# 合并所有数据
all_movies_df = douban_df.union(all_tmdb_df)
```

### Pandas 读取（小数据量）

```python
import pandas as pd

# 读取CSV
df = pd.read_csv("/home/zsy/films/cleaned_data/douban/19_20_cleaned.csv", encoding="utf-8")
```

## 九、评分数据提取

如需从评论中提取用户-电影评分矩阵，可使用以下逻辑：

```python
import re

def extract_ratings(reviews_str):
    ratings = []
    if not reviews_str:
        return ratings
    
    for part in reviews_str.split('[评论')[1:]:
        idx_end = part.find(']')
        if idx_end == -1:
            continue
        
        content = part[idx_end+1:].strip()
        author_match = re.search(r'作者:\s*([^|]+)', content)
        rating_match = re.search(r'评分:\s*([\d.]+)/10', content)
        
        if author_match and rating_match:
            ratings.append({
                "user_id": author_match.group(1).strip(),
                "rating": float(rating_match.group(1))
            })
    
    return ratings
```

提取后的评分数据格式：

| user_id | movie_id | rating |
|---------|----------|--------|
| 张小北 | 26266893 | 10.0 |
| MovieFan | 99861 | 6.5 |

## 十、数据质量说明

1. **繁简体转换**：所有中文内容已使用OpenCC转换为简体字
2. **字段标准化**：所有字段名统一为英文，多值字段统一使用竖线分隔
3. **空值填充**：根据字段重要性采用不同的填充策略
4. **评分统一**：豆瓣五星制已转换为10分制，与TMDb保持一致
5. **路径拼接**：封面路径已拼接完整路径前缀`./picture/`

## 十一、注意事项

1. **movie_id唯一性**：豆瓣和TMDb的movie_id可能重复，使用时需结合数据源区分
2. **时间格式**：release_date字段可能包含地区信息，如`2019-02-05(中国大陆)`
3. **多值字段**：解析时需处理单个值和空值的情况
4. **评分范围**：rating字段为10分制，评论中的评分也是10分制
5. **数据时效性**：评分和评分人数为采集时刻的快照数据