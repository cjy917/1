# 基于 Spark 的电影数据分析和推荐系统

厦门大学大数据编程实践课程项目，参考 [电影推荐系统案例](https://dblab.xmu.edu.cn/post/movierecommend/)。

## 功能概览

| 模块 | 功能 |
|------|------|
| 用户系统 | 注册、登录、退出 |
| 电影展示 | 海报、详情、**正片网页内播放**（本地 MP4 / 视频直链） |
| 评论翻译 | 英文爬虫评论一键翻译为中文 |
| 用户互动 | 0.5-10 分评分、发表评论 |
| 电影搜索 | 按名称、导演、演员、类型、简介搜索 |
| 数据分析 | ECharts 多维可视化（类型/年份/国家/评分/语言/Top10） |
| 智能推荐 | 四层算法：ALS(0.7) + GraphX(0.2) + TF-IDF内容(0.1) + 冷启动兜底 |

## 项目结构

```
xt1/
├── merged/                    # 已有爬虫数据（movies.csv/json + posters）
└── movie-system/
    ├── backend/               # Flask Web 后端
    ├── frontend/              # 前端页面（ECharts 可视化）
    ├── spark/                 # Spark Scala 程序（SQL/ALS/GraphX）
    ├── crawler/               # 爬虫扩展（TMDB API）
    ├── scripts/               # 数据导入脚本
    ├── start.bat              # Windows 一键启动
    └── start.sh               # Linux 一键启动
```

## 快速开始（Windows 合并版）

**前置：** MySQL 已导入 `movies_backup.sql`，`cs1/films_data` 与 `cs1/posters` 数据就绪。

```bat
cd movie-system\movie-system
pip install -r backend\requirements.txt
cd frontend && npm install && cd ..
start-system.bat
```

浏览器访问：**http://localhost:5173**（Vue 前端，API 代理到 5000）

打包生产模式（可选）：

```bat
cd frontend && npm run build
cd ..\backend && python app.py
```

访问：**http://127.0.0.1:5000**

## 快速开始（Linux / 实训环境）

```bash
cd movie-system2
chmod +x start.sh spark/run_spark_jobs.sh
./start.sh
```

## Spark 任务运行

### 1. 环境要求

- JDK 8+
- Maven 3.6+
- Spark 2.4+（Linux 伪分布式或本地模式）

### 2. 运行推荐与分析

在 **Ubuntu 虚拟机**（已安装 Spark）上执行：

```bash
cd movie-system2/movie-system2/spark
chmod +x run_spark_jobs.sh
./run_spark_jobs.sh
```

脚本会自动导出评分并运行 ALS、GraphX、TF-IDF 三个 Spark 推荐任务。

或在 Spark 集群上手动提交：

```bash
mvn clean package -DskipTests
spark-submit --class edu.xt1.spark.MovieRecommendALS target/movie-recommend-spark-1.0.0.jar spark/data/ratings.json spark/output/recommendations_als.json
spark-submit --class edu.xt1.spark.MovieRecommendGraphX target/movie-recommend-spark-1.0.0.jar spark/data/ratings.json spark/output/recommendations_graphx.json 8
spark-submit --class edu.xt1.spark.MovieRecommendContentBased target/movie-recommend-spark-1.0.0.jar ../../films_data spark/data/ratings.json spark/output/recommendations_content.json
```

### 3. 导入推荐结果

在 Web 页面「智能推荐」中点击 **导入 Spark 推荐结果**，或调用 API：

```bash
curl -X POST http://127.0.0.1:5000/api/spark/load-results
```

## 正片播放说明

系统**只播放电影正片**，不再播放预告片。播放优先级：

1. **本地 MP4**（推荐）：`merged/videos/{电影ID}.mp4`
2. **在线直链**：CSV / 数据库中的 `视频地址` 字段（MP4 直链）

### 添加正片方式

**方式一：直接放本地文件**
```
merged/videos/1023915.mp4
```

**方式二：CSV 增加视频地址列**
```csv
电影ID,中文名称,...,视频地址
1023915,2073年,...,https://example.com/movie.mp4
```
然后删除 `backend/movie_system.db` 重新导入，或手动更新数据库。

**方式三：脚本下载到本地**
```bash
python scripts/download_video.py --movie-id 1023915 --url https://example.com/movie.mp4
```

**查看已有正片：**
```bash
python scripts/list_videos.py
```

> 说明：TMDB 仅提供元数据和预告片，不含正版正片。正片需通过爬虫补充视频地址，或自行准备 MP4 文件。Internet Archive 公版电影可在 Linux 服务器上用 `scripts/fetch_videos.py` 批量关联。

## 爬虫扩展（补充至 5000+ 条）

当前 `merged/movies.csv` 约 **2708** 条，可使用 TMDB API 继续爬取：

```bash
pip install requests
python crawler/tmdb_crawler.py --api-key YOUR_TMDB_API_KEY --pages 50
python scripts/import_data.py   # 重新导入（需先删除 backend/movie_system.db）
```

TMDB API Key 申请：https://www.themoviedb.org/settings/api

## 技术栈

- **后端**: Python Flask + SQLite
- **前端**: HTML/CSS/JavaScript + ECharts
- **大数据**: Spark SQL、Spark MLlib ALS、Spark GraphX
- **翻译**: deep-translator（Google 翻译）
- **数据源**: TMDB 爬虫数据

## 创新点

1. **双算法推荐**：ALS 协同过滤 + GraphX 图 PageRank 融合
2. **英文评论翻译**：爬虫英文影评一键中文化
3. **可视化分析大屏**：6 维度 ECharts 交互图表
4. **内容相似推荐**：基于类型的相似电影推荐
5. **爬虫可扩展**：TMDB API 模块化补充数据

## 实训报告建议章节

1. 数据爬取及预处理（数据来源、字段说明、数据量）
2. Linux/Hadoop/Spark 环境搭建
3. Spark SQL 数据分析与可视化
4. Spark MLlib ALS 推荐算法原理与实现
5. GraphX 图推荐算法原理与实现
6. Web 系统功能演示（登录、搜索、评分、推荐）
7. 总结与展望

## 注意事项

- 爬虫请遵守网站 robots 协议，控制频率，不做破坏性爬取
- Spark 程序在 IntelliJ IDEA 中打开 `spark/` 目录即可开发调试
- 生产部署可将 SQLite 替换为 MySQL，数据导入 HDFS 后在集群运行 Spark
