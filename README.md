# Spark 电影推荐系统

基于 Vue3 + Flask + MySQL + Spark MLlib 构建的现代化电影推荐系统，包含用户认证、电影库管理、数据分析可视化、个性化推荐等核心功能。

---

## 📋 项目概览

| 模块 | 功能 | 技术实现 |
|------|------|----------|
| 电影推荐系统 | 完整 Web 应用（前后端） | Vue3 + Flask + MySQL |
| 数据处理 | 清洗、导入、评分提取 | Python + PySpark |
| 大数据分析 | Spark MLlib 推荐算法 | Spark 3.4+ |

---

## 📁 项目结构

```
FYWZ/                              # 项目根目录
├── movie-system/                  # Web 应用（前后端）
│   ├── backend/                   # Flask 后端
│   │   ├── services/              # 业务服务层（10+ 服务模块）
│   │   ├── app.py                 # 应用入口（50+ API 端点）
│   │   ├── config.py              # 配置文件
│   │   └── models.py              # SQLAlchemy 模型
│   ├── frontend/                  # Vue3 前端
│   │   ├── src/
│   │   │   ├── views/             # 页面视图（7个页面）
│   │   │   ├── analytics/         # 数据分析子模块
│   │   │   ├── components/        # 公共组件
│   │   │   └── router/            # 路由配置
│   │   └── package.json           # 前端依赖
│   ├── scripts/                   # 数据处理脚本
│   │   ├── clean_movies.py        # 数据清洗
│   │   ├── import_to_mysql.py     # MySQL 导入
│   │   ├── import_to_neo4j.py     # Neo4j 导入
│   │   ├── extract_ratings.py     # 评分提取
│   │   ├── movie_recommendation.py # 推荐算法示例
│   │   └── download_home_trailers.py # 预告片下载
│   ├── spark/                     # Spark 大数据脚本
│   │   └── movie_recommend_als.py # Spark MLlib ALS 推荐
│   ├── start-system.bat           # 一键启动脚本
│   └── README.md                  # 【详细系统文档】
│
├── films_data/                    # 清洗后的数据（需解压）
│   ├── cleaned_data/              # 电影数据
│   │   ├── douban/                # 豆瓣数据
│   │   └── tmdb/                  # TMDb 数据
│   ├── ratings/                   # 评分数据
│   └── docs/                      # 数据文档
│       ├── data_dictionary.md     # 数据字典
│       └── handover_document.md   # 交接文档
│
├── docs/                          # 项目文档
│   └── data_dictionary.md         # 数据字典（副本）
├── movies_backup.sql              # MySQL 数据库备份（21MB）
└── README.md                      # 项目总览（本文件）
```

---

## 🔗 文档导航

| 文档 | 位置 | 内容 |
|------|------|------|
| **系统详细文档** | [movie-system/README.md](movie-system/README.md) | API 接口、模块协作、配置说明、扩展指南 |
| 数据字典 | [docs/data_dictionary.md](docs/data_dictionary.md) | 字段定义、数据格式、注意事项 |
| Spark 推荐脚本 | [movie-system/spark/movie_recommend_als.py](movie-system/spark/movie_recommend_als.py) | MLlib ALS 分布式推荐算法 |

---

## 🚀 快速启动

### 1. 环境要求

- Python 3.8+
- Node.js 18+
- MySQL 8.0+
- Java 8+（Spark 需要）

### 2. 导入数据库

```bash
mysql -u root -p123456 -e "CREATE DATABASE IF NOT EXISTS movies_db;"
mysql -u root -p123456 movies_db < movies_backup.sql
```

### 3. 启动系统

**方式一：一键启动（Windows）**

```bash
cd movie-system
.\start-system.bat
```

**方式二：手动启动**

```bash
# 后端
cd movie-system/backend
pip install -r requirements.txt
python app.py

# 前端（新终端）
cd movie-system/frontend
npm install --legacy-peer-deps
npm run dev
```

### 4. 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://127.0.0.1:5173 |
| 后端 | http://127.0.0.1:5000 |
| 后端健康检查 | http://127.0.0.1:5000/api/health |

---

## 📊 数据规模

| 数据项 | 数量 |
|--------|------|
| 电影总数 | 6766 部 |
| 爬取评分 | 约 33830 条 |
| 数据来源 | 豆瓣 + TMDb |
| 时间范围 | 2015-2026 年 |

---

## 🛠 核心脚本说明

### 数据处理脚本（movie-system/scripts/）

| 脚本 | 功能 | 使用方式 |
|------|------|----------|
| `clean_movies.py` | 数据清洗（去重、格式统一） | `python clean_movies.py` |
| `import_to_mysql.py` | 将 CSV/Parquet 导入 MySQL | `python import_to_mysql.py` |
| `import_to_neo4j.py` | 将数据导入 Neo4j（图数据库） | `python import_to_neo4j.py` |
| `extract_ratings.py` | 从评论中提取用户评分 | `python extract_ratings.py` |
| `movie_recommendation.py` | 推荐算法示例（ALS/NMF） | `python movie_recommendation.py` |
| `download_home_trailers.py` | 预告片下载（支持真实预告/演示模式） | `python download_home_trailers.py --mode real` |

### Spark 脚本（movie-system/spark/）

| 脚本 | 功能 | 使用方式 |
|------|------|----------|
| `movie_recommend_als.py` | Spark MLlib ALS 协同过滤推荐 | `spark-submit movie_recommend_als.py` |

---

## 🔧 扩展开发

### 添加新数据分析维度

详细步骤请参考 [movie-system/README.md](movie-system/README.md) 的「扩展指南」章节。

### Spark 集群部署

```bash
spark-submit \
  --master spark://master:7077 \
  --deploy-mode cluster \
  --py-files services.zip \
  movie-system/spark/movie_recommend_als.py
```

---

## ❓ 常见问题

### Q1：系统启动失败？

确保 MySQL 已启动并导入 `movies_backup.sql`，检查 [movie-system/README.md](movie-system/README.md) 的「配置说明」章节。

### Q2：数据文件在哪里？

数据文件 `films_data.tar.gz` 需要解压到项目根目录。

### Q3：如何获取系统详细文档？

请查看 [movie-system/README.md](movie-system/README.md)，包含完整的 API 文档、模块协作流程和配置说明。

---

## 📝 参考文档

- [movie-system/README.md](movie-system/README.md) — 完整系统文档
- [docs/data_dictionary.md](docs/data_dictionary.md) — 详细数据字典
- [movie-system/spark/movie_recommend_als.py](movie-system/spark/movie_recommend_als.py) — Spark 推荐算法