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
| 数据分析 | ECharts 多维可视化（类型/年份/国家/评分/语言/Top10/词云等） |
| 智能推荐 | 四层算法：NMF-ALS(0.7) + GraphX(0.2) + TF-IDF内容(0.1) + 冷启动兜底 |

## 项目结构

```
FYWZ/
├── films_data/          # 爬虫数据目录（MySQL导入源）
│   ├── ratings/         # 爬虫评分 CSV
│   └── picture/         # 海报图片
├── posters/             # 海报目录（多路径兼容）
├── trailers/            # 本地预告片目录
├── videos/              # 本地正片视频目录
└── movie-system/        # 系统主目录
    ├── backend/         # Flask Web 后端
    │   ├── services/    # 业务服务层
    │   ├── app.py       # 应用入口
    │   ├── config.py    # 配置文件
    │   └── models.py    # SQLite模型
    ├── frontend/        # Vue3 前端页面（ECharts 可视化）
    ├── spark/           # Spark Scala 程序（SQL/ALS/GraphX）
    ├── crawler/         # 爬虫扩展（TMDB API）
    ├── scripts/         # 数据导入脚本
    ├── media/           # 媒体演示文件（demo.mp4）
    ├── start-system.bat # Windows 一键启动
    ├── start-system.ps1 # PowerShell 一键启动
    └── start-backend-only.bat # 仅启动后端
```

## 快速开始（Windows）

**前置：** MySQL 已导入 `movies_backup.sql`，数据文件就绪。

```bat
cd movie-system
pip install -r backend\requirements.txt
cd frontend && npm.cmd install --legacy-peer-deps && cd ..
start-system.bat
```

浏览器访问：**http://localhost:5173**（Vue 前端，API 代理到 5000）

打包生产模式（可选）：

```bat
cd frontend && npm.cmd run build
cd ..\backend && python app.py
```

访问：**http://127.0.0.1:5000**

## 快速开始（Linux / 实训环境）

```bash
cd movie-system
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
cd movie-system/spark
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

## 媒体播放说明

电影详情页支持**正片播放**和**预告片播放**，通过标签页切换。

### 正片播放优先级：

1. **本地 MP4**（推荐）：`videos/{电影ID}.mp4`
2. **在线直链**：CSV / 数据库中的 `视频地址` 字段（MP4 直链）

### 预告片播放优先级：

1. **本地 MP4**：`trailers/{电影ID}.mp4`
2. **TMDB YouTube 链接**：通过 TMDB API 获取官方预告片 YouTube 链接
3. **B站链接**：通过 TMDB 返回的视频 ID 匹配 B站资源

### 添加正片方式

**方式一：直接放本地文件**
```
videos/1023915.mp4
```

**方式二：CSV 增加视频地址列**
```csv
电影ID,中文名称,...,视频地址
1023915,2073年,...,https://example.com/movie.mp4
```
然后删除 `backend/app.db` 重新导入，或手动更新数据库。

**方式三：脚本下载到本地**
```bash
python scripts/download_video.py --movie-id 1023915 --url https://example.com/movie.mp4
```

**查看已有正片：**
```bash
python scripts/list_videos.py
```

> 说明：TMDB 仅提供元数据和预告片，不含正版正片。正片需通过爬虫补充视频地址，或自行准备 MP4 文件。Internet Archive 公版电影可在 Linux 服务器上用 `scripts/fetch_videos.py` 批量关联。

## 数据来源说明

系统数据来源于**豆瓣**和**TMDb**两个平台，已爬取完成并存储在 `films_data/` 目录下，数据规模固定为 **6766** 部电影。

### 数据源结构

```
films_data/cleaned_data/
├── douban/                    # 豆瓣数据（2019-2020年，约1535部）
│   └── 19_20_cleaned.parquet/
└── tmdb/                      # TMDb数据（2015-2026年，约5200部）
    ├── 2015_cleaned.parquet/
    ├── 2016_cleaned.parquet/
    ├── 2017_cleaned.parquet/
    ├── 2018_cleaned.parquet/
    ├── 21_22_cleaned.parquet/
    ├── 23_24_cleaned.parquet/
    └── 25_26_cleaned.parquet/
```

### 爬取方式

| 平台 | 爬取方式 | 认证方式 | 数据特点 |
|------|---------|---------|---------|
| **豆瓣** | 网页爬虫（解析HTML DOM） | Cookie登录态 | 中文数据完整，包含详细短评 |
| **TMDb** | 官方API（RESTful JSON） | API Key参数 | 英文数据为主，字段标准化 |

### 数据导入

数据已通过 `movies_backup.sql` 导入 MySQL，启动系统前确保数据库已恢复：

```bash
mysql -u root -p movies_db < movies_backup.sql
```

## 技术栈

- **后端**: Python Flask + SQLite（用户数据）+ MySQL（电影数据）
- **前端**: Vue3 + Vite + ECharts + Element Plus + Pinia + Tailwind CSS + vue-router + axios
- **大数据**: Spark SQL、Spark MLlib ALS、Spark GraphX
- **翻译**: deep-translator（Google 翻译）
- **数据源**: TMDB API 爬虫数据

---

## 数据预处理

### 数据源

| 数据源 | 文件 | 记录数 | 来源 |
|--------|------|--------|------|
| 豆瓣 | `cleaned_data/douban/19_20_cleaned.parquet` | ~1535条 | 网页爬虫（Cookie登录） |
| TMDb | `cleaned_data/tmdb/*.parquet` | ~5200条 | 官方API（API Key） |
| 合并 | `movies_backup.sql` | ~6766条 | MySQL备份 |

### 预处理流程

预处理由 `scripts/clean_movies.py` 使用 PySpark 完成，流程如下：

1. **字段重命名**：将中文列名统一映射为英文列名
   - "豆瓣电影ID"/"电影ID" → `movie_id`
   - "中文名称" → `title`
   - "评分" → `rating`
   - "上映日期" → `release_date`
   - "导演" → `directors`
   - "主演" → `actors`
   - "影片类型" → `genres`
   - "制片国家/地区" → `countries`
   - 共映射 22 个字段

2. **数据清洗规则**：
   - **空值过滤**：删除 `movie_id` 或 `title` 为空的记录
   - **格式校验**：`movie_id` 必须为纯数字格式
   - **繁简转换**：使用 OpenCC 将繁体字转换为简体字（title、aliases、summary、reviews、directors、writers、actors）
   - **换行符替换**：将 `reviews` 和 `summary` 中的 `\r\n` 替换为空格
   - **多值字段标准化**：directors、writers、actors、languages、genres、countries、aliases 使用 `|` 分隔，去除首尾和连续的 `|`
   - **类型转换**：rating(Float)、rating_count(Integer)、review_count(Integer)、release_year(Integer)
   - **默认值填充**：aliases 为空填"未知"，awards 为空填"无"，rating 为空填 0.0

3. **评分提取**：
   - 由 `scripts/extract_ratings.py` 从评论文本中提取用户评分
   - 每条评论格式：`[评论N]作者:xxx|评分:x.x/10 评论内容`
   - 提取字段：user_id、rating、comment、source
   - 过滤条件：rating > 0
   - 提取结果：约 33830 条评分数据

4. **输出格式**：
   - CSV 格式：用于 MySQL 导入
   - Parquet 格式：用于 Spark 分布式计算

---

## 模型与代码

### 推荐算法模型表达

#### NMF-ALS 在线协同过滤

**模型公式**：
```
R ≈ U × V^T

其中：
  R ∈ R^(n_users × n_movies)  — 用户-电影评分矩阵（稀疏）
  U ∈ R^(n_users × n_components)  — 用户特征矩阵
  V ∈ R^(n_movies × n_components)  — 物品特征矩阵
  n_components = min(20, n_movies-1, n_users-1)  — 隐因子维度

损失函数：
  L = ||R - UV^T||_F^2 + λ(||U||_F^2 + ||V||_F^2)

优化配置：
  init = "nndsvda"  — 非负双重奇异值分解初始化
  max_iter = 300  — 最大迭代次数
  random_state = 42  — 随机种子（保证可复现）
```

#### 混合推荐权重公式

```
Score(movie) = Weight_ALS × Score_ALS + Weight_GraphX × Score_GraphX + Weight_Content × Score_Content

其中：
  Weight_ALS = 0.7（协同过滤为主）
  Weight_GraphX = 0.2（图相似扩展）
  Weight_Content = 0.1（内容相似兜底）
```

### 核心函数伪代码

#### 1. recommend_als_for_user（NMF-ALS 在线推荐）

```python
# 文件: backend/services/recommend_service.py, 行74-107
# 输入: user_id(int) - 用户ID, limit(int) - 推荐数量
# 输出: list[dict] - 推荐电影列表

def recommend_als_for_user(user_id, limit=12):
    1. 构建评分矩阵
       ├─ user_map = {用户名 → 矩阵行索引}
       ├─ movie_map = {电影ID → 矩阵列索引}
       ├─ 遍历 CrawledRating 和 UserRating 表
       └─ matrix[uid, mid] = score  # 填充评分矩阵
    
    2. 检查数据有效性
       └─ 如果矩阵为空或用户不在映射中，返回热门电影兜底
    
    3. NMF 分解
       ├─ n_components = min(20, 电影数-1, 用户数-1)
       ├─ model = NMF(n_components, init="nndsvda", max_iter=300, random_state=42)
       ├─ U = model.fit_transform(matrix)  # 用户特征
       └─ V = model.components_.T          # 物品特征
    
    4. 预测评分
       └─ predicted = U[用户索引] × V^T
    
    5. 过滤与排序
       ├─ 排除用户已评分的电影
       ├─ 按预测评分降序排序
       └─ 取前 limit × 2 部电影（为后续选择留余量）
    
    6. 获取电影详情
       └─ 调用 get_movies_by_ids(movie_ids) 获取完整信息
    
    7. 返回结果
       └─ 返回前 limit 部电影
    
    异常处理：
       └─ NMF 失败时降级为内容相似推荐或热门电影兜底
```

#### 2. _online_hybrid_recommendations（在线混合推荐）

```python
# 文件: backend/services/recommendation_service.py, 行346-430
# 输入: user_id(int) - 用户ID, rating_count(int) - 用户评分数量
# 输出: dict - 混合推荐结果

def _online_hybrid_recommendations(user_id, rating_count):
    1. 获取用户已评分电影ID集合
       └─ rated_movie_ids = {str(r.movie_id) for r in UserRating.query.filter_by(user_id=user_id)}
    
    2. 并行计算三种算法得分
       ├─ als_norm = _online_als_scores(user_id, pool, rated_movie_ids)
       ├─ graphx_norm, graphx_reasons = _online_graphx_scores(user_id, pool, rated_movie_ids)
       └─ content_scores, content_reasons = _content_recommendations_for_user(user_id, pool, rated_movie_ids)
    
    3. 加权融合
       ├─ fused[mid]["score"] += als_norm[mid] × 0.7
       ├─ fused[mid]["score"] += graphx_norm[mid] × 0.2
       └─ fused[mid]["score"] += content_scores[mid] × 0.1
    
    4. 归一化与排序
       └─ 按融合得分降序排序，取前 20 部
    
    5. 组装推荐卡片
       ├─ 调用 _movie_card() 添加海报、评分、推荐理由
       └─ 生成 als_items、graphx_items、content_items 独立列表
    
    6. 返回结果
       └─ 返回混合推荐及各算法独立结果
```

#### 3. hybrid_recommendations（推荐入口）

```python
# 文件: backend/services/recommendation_service.py, 行718-739
# 输入: user_id(int) - 用户ID
# 输出: dict - 最终推荐结果

def hybrid_recommendations(user_id):
    1. 确保爬虫评分已加载
       └─ _ensure_crawled_ratings()
    
    2. 获取用户评分数量
       └─ rating_count = UserRating.query.filter_by(user_id=user_id).count()
    
    3. 判断冷启动状态
       ├─ 如果 rating_count < 3（冷启动）
       │   └─ 返回热门电影列表，strategy = "cold_start"
       └─ 如果 rating_count >= 3（正常推荐）
           └─ 调用 _spark_hybrid_recommendations(user_id, rating_count)
    
    4. 返回推荐策略信息
       └─ 包含 strategy、source、rating_count、personalized_ready 等元信息
```

### 跨子系统接口调用

| 调用方 | 被调用方 | 接口/函数 | 文件路径 |
|--------|----------|-----------|----------|
| Flask API | 电影服务 | `get_movie_by_id(movie_id)` | `services/movie_service.py` |
| Flask API | 推荐服务 | `hybrid_recommendations(user_id)` | `services/recommendation_service.py` |
| Flask API | 数据分析服务 | `overview_stats(...)` | `services/analytics_service.py` |
| 推荐服务 | 电影服务 | `get_movies_by_ids(movie_ids)` | `services/movie_service.py` |
| 推荐服务 | 推荐算法 | `recommend_als_for_user(user_id, limit)` | `services/recommend_service.py` |
| 数据分析服务 | 电影服务 | `get_mysql()` | `services/movie_service.py` |
| 推荐服务 | Spark VM | `run_spark_pipeline_on_vm()` | `services/spark_vm_client.py` |

---

## 系统设计文档

### 用例图

**参与者**：
- 用户（普通用户）
- 管理员

**用户用例**：
1. 注册 — 用户输入用户名、邮箱、密码完成注册
2. 登录 — 用户输入用户名、密码登录系统
3. 浏览电影 — 用户查看首页电影列表、详情页
4. 搜索电影 — 用户按关键词搜索电影
5. 评分电影 — 用户对电影进行 0.5-10 分评分
6. 发表评论 — 用户发表电影评论
7. 收藏电影 — 用户将电影加入收藏夹
8. 添加待看 — 用户将电影加入待看片单
9. 查看推荐 — 用户查看个性化推荐列表
10. 查看数据分析 — 用户查看电影数据可视化分析

**管理员用例**：
1. 导入 Spark 推荐结果 — 管理员将 Spark 批处理结果导入数据库
2. 导出评分数据 — 管理员导出评分数据供 Spark 计算使用

### ER 图

**实体列表**（共 10 张表）：

#### 1. movies（MySQL，通过 SQL 备份导入）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | bigint | PRIMARY KEY, AUTO_INCREMENT | 自增主键 |
| movie_id | bigint | NOT NULL, UNIQUE | 电影唯一标识 |
| title | varchar(200) | NOT NULL | 电影标题 |
| rating | float | DEFAULT 0 | 豆瓣评分 |
| rating_count | int | DEFAULT 0 | 评分人数 |
| release_date | varchar(50) | NULL | 上映日期 |
| release_year | int | DEFAULT 0 | 上映年份 |
| directors | varchar(1000) | NULL | 导演（\|分隔） |
| writers | varchar(1000) | NULL | 编剧（\|分隔） |
| actors | varchar(2000) | NULL | 主演（\|分隔） |
| aliases | varchar(2000) | NULL | 别名（\|分隔） |
| summary | text | NULL | 简介 |
| detail_url | varchar(500) | NULL | 详情页链接 |
| languages | varchar(500) | NULL | 语言（\|分隔） |
| genres | varchar(500) | NULL | 类型（\|分隔） |
| duration | varchar(50) | NULL | 片长 |
| reviews | text | NULL | 评论内容 |
| countries | varchar(500) | NULL | 国家（\|分隔） |
| awards | varchar(2000) | NULL | 获奖情况 |
| review_count | int | DEFAULT 0 | 影评数 |
| cover_path | varchar(200) | NULL | 封面路径 |
| source | varchar(20) | NULL | 数据来源 |

#### 2. users（SQLite）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PRIMARY KEY | 用户ID |
| username | String(80) | UNIQUE, NOT NULL | 用户名 |
| email | String(120) | UNIQUE, NOT NULL | 邮箱 |
| password_hash | String(256) | NOT NULL | 密码哈希 |
| created_at | DateTime | DEFAULT utcnow | 创建时间 |

#### 3. user_ratings（SQLite）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PRIMARY KEY | 评分记录ID |
| user_id | Integer | FOREIGN KEY → users(id) | 用户ID |
| movie_id | BigInteger | NOT NULL | 电影ID |
| score | Float | NOT NULL | 评分（0.5-10） |
| created_at | DateTime | DEFAULT utcnow | 创建时间 |
| updated_at | DateTime | DEFAULT utcnow | 更新时间 |

#### 4. favorites（SQLite）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PRIMARY KEY | 收藏记录ID |
| user_id | Integer | FOREIGN KEY → users(id) | 用户ID |
| movie_id | BigInteger | NOT NULL | 电影ID |
| created_at | DateTime | DEFAULT utcnow | 创建时间 |

#### 5. watchlists（SQLite）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PRIMARY KEY | 待看记录ID |
| user_id | Integer | FOREIGN KEY → users(id) | 用户ID |
| movie_id | BigInteger | NOT NULL | 电影ID |
| created_at | DateTime | DEFAULT utcnow | 创建时间 |

#### 6. user_list_items（SQLite）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PRIMARY KEY | 片单记录ID |
| user_id | Integer | FOREIGN KEY → users(id) | 用户ID |
| movie_id | BigInteger | NOT NULL | 电影ID |
| created_at | DateTime | DEFAULT utcnow | 创建时间 |

#### 7. movie_comments（SQLite）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PRIMARY KEY | 评论记录ID |
| user_id | Integer | FOREIGN KEY → users(id) | 用户ID |
| movie_id | BigInteger | NOT NULL | 电影ID |
| content | Text | NOT NULL | 评论内容 |
| score | Float | NULL | 评分 |
| created_at | DateTime | DEFAULT utcnow | 创建时间 |
| updated_at | DateTime | DEFAULT utcnow | 更新时间 |

#### 8. crawled_ratings（SQLite）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PRIMARY KEY | 爬虫评分记录ID |
| user_name | String(120) | NOT NULL | 爬虫用户名 |
| movie_id | BigInteger | NOT NULL | 电影ID |
| score | Float | NOT NULL | 评分 |
| source | String(20) | DEFAULT "douban" | 数据来源 |

#### 9. recommendation_cache（SQLite）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PRIMARY KEY | 缓存记录ID |
| user_id | Integer | FOREIGN KEY → users(id) | 用户ID |
| movie_id | BigInteger | NOT NULL | 电影ID |
| score | Float | NOT NULL | 推荐得分 |
| algorithm | String(32) | DEFAULT "als" | 算法类型 |
| created_at | DateTime | DEFAULT utcnow | 创建时间 |

#### 10. spark_recommendations（SQLite）
| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PRIMARY KEY | 推荐记录ID |
| user_id | Integer | FOREIGN KEY → users(id) | 用户ID |
| movie_id | BigInteger | NOT NULL | 电影ID |
| score | Float | NOT NULL | 推荐得分 |
| algorithm | String(32) | NOT NULL | 算法类型（als/graphx/content） |
| created_at | DateTime | DEFAULT utcnow | 创建时间 |

**关系说明**：
- users 与 user_ratings：1:N（一个用户多条评分）
- users 与 favorites：1:N（一个用户多个收藏）
- users 与 watchlists：1:N（一个用户多个待看）
- users 与 user_list_items：1:N（一个用户多个片单项）
- users 与 movie_comments：1:N（一个用户多条评论）
- users 与 recommendation_cache：1:N（一个用户多条推荐缓存）
- users 与 spark_recommendations：1:N（一个用户多条 Spark 推荐）
- movies 表无外键关系（独立存在，通过 movie_id 与其他表关联）

### 功能模块图

```
电影推荐系统
├── 用户认证模块
│   ├── 注册
│   ├── 登录
│   └── 退出
│
├── 电影展示模块
│   ├── 首页展示（Hero轮播、热门、高分、新上映）
│   ├── 电影详情（基本信息、评论、评分、海报）
│   └── 电影搜索（关键词、类型、年份、语言筛选）
│
├── 用户互动模块
│   ├── 评分（0.5-10分）
│   ├── 评论（发表、删除）
│   ├── 收藏
│   ├── 待看片单
│   └── 我的片单
│
├── 数据分析模块
│   ├── 概览统计（电影数、用户数、评分数）
│   ├── 类型分布
│   ├── 年份分布
│   ├── 国家分布
│   ├── 评分分布
│   ├── 语言分布
│   ├── 演员分布
│   ├── 导演分布
│   ├── 时长分布
│   ├── 评论数分布
│   ├── 国家-类型关联
│   ├── 评分-时长关联
│   ├── 获奖分布
│   ├── 月度上映分布
│   ├── 词云数据
│   └── Top榜单
│
├── 智能推荐模块
│   ├── 冷启动推荐（热门电影兜底）
│   ├── 在线 NMF-ALS 协同过滤
│   ├── 在线 GraphX 图相似推荐
│   ├── 内容相似推荐（TF-IDF）
│   ├── 混合推荐（加权融合）
│   └── Spark 离线推荐导入
│
└── 媒体播放模块
    ├── 预告片播放
    ├── 正片播放
    └── 海报展示
```

### 数据流图

**顶层数据流图（Level 0）**：
```
用户 ──HTTP请求──→ Flask API ──SQL查询──→ MySQL(movies)
    ←──HTTP响应──        ──SQL查询──→ SQLite(users, ratings, favorites...)
                        ──调用──→ Spark VM（离线推荐计算）
```

**推荐子系统数据流（Level 1）**：
```
用户请求 /api/recommend/personal
        │
        ▼
┌─────────────────────────────────────────┐
│ hybrid_recommendations(user_id)          │
└─────────────────────────────────────────┘
        │
        ├── rating_count < 3 ──→ 冷启动模式 ──→ 返回热门电影
        │
        └── rating_count >= 3
                │
                ├── 在线路径（实时计算）
                │       │
                │       ├── _online_als_scores() ──→ NMF分解评分矩阵
                │       ├── _online_graphx_scores() ──→ 图相似扩展
                │       └── _content_recommendations_for_user() ──→ TF-IDF内容相似
                │               │
                │               ▼
                │       加权融合（ALS×0.7 + GraphX×0.2 + Content×0.1）
                │
                └── 离线路径（Spark批处理）
                        │
                        ├── 读取 spark/output/recommendations_*.json
                        ├── 归一化各算法得分
                        └── 加权融合输出
                │
                ▼
        返回推荐结果（包含混合推荐 + 各算法独立结果）
```

**数据分析子系统数据流（Level 1）**：
```
用户请求 /api/analytics/*
        │
        ▼
┌─────────────────────────────────────────┐
│ analytics_service.py 各统计函数          │
└─────────────────────────────────────────┘
        │
        ├── _parse_filters() ──→ 解析 genre/year/country 过滤条件
        │
        └── get_mysql() ──→ MySQL movies 表查询
                │
                ▼
        返回统计数据（JSON格式）
                │
                ▼
        前端 ECharts 可视化渲染
```

### 架构图

**系统架构分层**：
```
┌─────────────────────────────────────────────────────────┐
│                    前端层（Vue3）                         │
│  ┌─────────┬─────────┬─────────┬─────────┬─────────┐   │
│  │ HomeView│MovieView│Recommend│Analytic │AuthView │   │
│  │         │ Detail  │View     │View     │         │   │
│  └────┬────┴────┬────┴────┬────┴────┬────┴────┬────┘   │
│       │         │         │         │         │         │
└───────┼─────────┼─────────┼─────────┼─────────┼─────────┘
        │         │         │         │         │
        ▼         ▼         ▼         ▼         ▼
┌─────────────────────────────────────────────────────────┐
│                    API层（Flask）                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │ app.py（50+ API端点）                           │    │
│  │ - /api/auth/*     用户认证                      │    │
│  │ - /api/movies/*   电影管理                      │    │
│  │ - /api/ratings    评分管理                      │    │
│  │ - /api/favorites  收藏管理                      │    │
│  │ - /api/comments   评论管理                      │    │
│  │ - /api/analytics/* 数据分析                     │    │
│  │ - /api/recommend/* 推荐服务                     │    │
│  │ - /api/spark/*    Spark集成                     │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                    服务层（Python）                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │movie_service │  │recommend_    │  │recommendation│  │
│  │.py           │  │service.py    │  │_service.py   │  │
│  │- MySQL查询   │  │- NMF-ALS算法 │  │- 混合推荐策略 │  │
│  │- 电影数据    │  │- 评分矩阵    │  │- 冷启动处理   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │analytics_    │  │trailer_      │  │spark_vm_     │  │
│  │service.py    │  │service.py    │  │client.py     │  │
│  │- 统计分析    │  │- 预告片处理  │  │- Spark远程调用│  │
│  │- 可视化数据  │  │              │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                    数据层                                 │
│  ┌──────────────────────────┐  ┌──────────────────────┐ │
│  │     MySQL（movies表）     │  │   SQLite（用户数据）  │ │
│  │ - 6766部电影             │  │ - users（用户）      │ │
│  │ - 22个字段               │  │ - user_ratings（评分）│ │
│  │ - 通过 SQL 备份导入       │  │ - favorites（收藏）  │ │
│  │                         │  │ - movie_comments（评论）│
│  └──────────────────────────┘  └──────────────────────┘ │
│  ┌──────────────────────────┐  ┌──────────────────────┐ │
│  │     Spark（离线计算）     │  │   文件系统           │ │
│  │ - ALS 协同过滤           │  │ - posters/（海报）   │ │
│  │ - GraphX 图推荐          │  │ - trailers/（预告片）│ │
│  │ - TF-IDF 内容推荐        │  │ - videos/（正片）    │ │
│  └──────────────────────────┘  └──────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**关键设计说明**：
- **双数据库架构**：movies 表使用 MySQL（数据量大、查询性能要求高），用户相关表使用 SQLite（轻量、快速开发）
- **movies 表特殊处理**：未在 models.py 中定义，通过 `movies_backup.sql` 导入 MySQL，由 `movie_service.py` 使用 PyMySQL 直接查询
- **推荐双模式**：在线模式（NMF-ALS 实时计算）+ 离线模式（Spark 批处理），用户评分 >= 3 时自动切换

---

## 创新点

1. **四层混合推荐**：NMF-ALS 协同过滤 + GraphX 图 PageRank + TF-IDF 内容相似 + 冷启动热门兜底
2. **英文评论翻译**：爬虫英文影评一键中文化
3. **多维可视化分析**：16+ 维度 ECharts 交互图表（类型/年份/国家/评分/语言/演员/导演/时长/词云等）
4. **双数据库架构**：MySQL（电影数据）+ SQLite（用户数据），兼顾性能与开发效率
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