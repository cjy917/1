# FYWZ 电影推荐系统 - 答辩关键内容

## 一、项目概览

基于 **Vue3 + Flask + MySQL + Spark MLlib** 构建的现代化电影推荐系统，包含用户认证、电影库管理、数据分析可视化、个性化推荐等核心功能。

**详细文档**：[movie-system/README.md](../../README.md)

---

## 二、关键设计 - 双数据库架构

### 2.1 movies 表特殊处理

**问题：** `movies` 表为什么没有在 [models.py](models.py) 中定义？

**回答：**

| 原因 | 说明 |
|------|------|
| 数据量 | 6766 部电影，22 个字段，包含长文本（summary、reviews） |
| 查询需求 | 需要 MySQL 的全文检索和高性能查询能力 |
| 导入方式 | 通过 SQL 备份文件 [movies_backup.sql](../../../movies_backup.sql) 导入 MySQL |
| 查询方式 | 由 [movie_service.py](services/movie_service.py) 使用 PyMySQL 直接查询 |

**表结构定义位置**：[movies_backup.sql](../../../movies_backup.sql)

### 2.2 数据库分工

```
┌─────────────────────────────────────┐
│          SQLite（app.db）           │
│  - users          用户表           │
│  - user_ratings   用户评分表       │
│  - favorites      收藏表           │
│  - movie_comments 评论表           │
│  - crawled_ratings 爬虫评分表     │
│  - recommendation_cache 推荐缓存   │
│  - spark_recommendations Spark推荐│
│  使用 SQLAlchemy ORM              │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│            MySQL（movies_db）       │
│  - movies         电影核心表        │
│    * 6766条记录，22个字段          │
│    * 通过 movies_backup.sql 导入   │
│    * 使用 PyMySQL 直接查询         │
└─────────────────────────────────────┘
```

---

## 三、功能模块与接口

### 3.1 模块清单

| 模块 | API 前缀 | 核心文件 | 功能说明 |
|------|----------|----------|----------|
| 用户认证 | `/api/auth` | [app.py](app.py) | 注册、登录、退出、获取当前用户 |
| 电影展示 | `/api/movies` | [movie_service.py](services/movie_service.py) | 列表、详情、搜索、相似电影 |
| 用户互动 | `/api/ratings` `/api/favorites` `/api/comments` | [models.py](models.py) | 评分、收藏、评论、待看片单 |
| 数据分析 | `/api/analytics` | [analytics_service.py](services/analytics_service.py) | 统计分析、可视化数据 |
| 智能推荐 | `/api/recommend` | [recommendation_service.py](services/recommendation_service.py) | 个性化推荐、混合算法 |
| Spark 集成 | `/api/spark` | [spark_vm_client.py](services/spark_vm_client.py) | 离线推荐计算、结果导入 |
| 视频播放 | `/api/videos` `/api/trailers` | [video_service.py](services/video_service.py) | 正片、预告片流服务 |

### 3.2 核心 API 接口

#### 用户认证

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/auth/register` | POST | 用户注册 | 否 |
| `/api/auth/login` | POST | 用户登录 | 否 |
| `/api/auth/logout` | POST | 用户退出 | 是 |
| `/api/auth/me` | GET | 获取当前用户 | 否 |

#### 电影数据

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/movies` | GET | 电影列表（分页/筛选/排序） |
| `/api/movies/:id` | GET | 电影详情 |
| `/api/movies/home` | GET | 首页电影区块 |
| `/api/movies/search` | GET | 搜索建议 |
| `/api/movies/:id/similar` | GET | 相似电影 |

#### 用户互动

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/ratings` | POST/DELETE | 评分（0.5-10分） | 是 |
| `/api/favorites` | GET/POST/DELETE | 收藏夹 | 是 |
| `/api/watchlist` | GET/POST/DELETE | 待看片单 | 是 |
| `/api/comments` | GET/POST/DELETE | 评论 | 是 |

#### 智能推荐

| 接口 | 方法 | 说明 | 认证 |
|------|------|------|------|
| `/api/recommend/personal` | GET | 个性化推荐 | 是 |
| `/api/recommend/guest` | GET | 游客推荐（冷启动） | 否 |
| `/api/recommend/similar/:id` | GET | 相似电影推荐 | 否 |
| `/api/recommend/refresh` | POST | 刷新推荐（触发Spark） | 是 |

#### 数据分析

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/analytics/overview` | GET | 概览统计 |
| `/api/analytics/genres` | GET | 类型分布 |
| `/api/analytics/countries` | GET | 国家分布 |
| `/api/analytics/ratings` | GET | 评分分布 |
| `/api/analytics/rating-leaderboard` | GET | 评分排行榜 |
| `/api/analytics/wordcloud` | GET | 词云数据 |

---

## 四、推荐系统关键算法

### 4.1 混合推荐策略

**权重分配**（定义在 [config.py](config.py)）：

| 算法 | 权重 | 作用 |
|------|------|------|
| NMF-ALS 协同过滤 | 0.7 | 主要推荐算法，基于用户行为 |
| GraphX 图相似 | 0.2 | 扩展推荐范围，发现关联电影 |
| TF-IDF 内容推荐 | 0.1 | 补充推荐，基于电影内容相似性 |

**推荐策略流程图**：

```
用户请求个性化推荐
        │
        ▼
┌─────────────────────────────┐
│ hybrid_recommendations()    │  [recommendation_service.py]
└─────────────────────────────┘
        │
        ├── 用户评分 < 3 ──→ 冷启动模式 ──→ 返回热门电影
        │
        └── 用户评分 >= 3
                │
                ├── 有 Spark 离线结果 ──→ 加载 Spark JSON ──→ 加权融合
                │
                └── 无 Spark 结果 ──→ 在线混合推荐
                        │
                        ├── NMF-ALS 得分 × 0.7
                        ├── GraphX 得分 × 0.2
                        └── TF-IDF 得分 × 0.1
                                │
                                ▼
                        归一化排序 → 返回推荐结果
```

### 4.2 NMF-ALS 算法伪代码

**文件**：[recommend_service.py](services/recommend_service.py) - `recommend_als_for_user()`

```python
# 输入: user_id(int) - 用户ID, limit(int) - 推荐数量
# 输出: list[dict] - 推荐电影列表

def recommend_als_for_user(user_id, limit=12):
    # 步骤1: 构建评分矩阵
    user_map = {}  # {用户名 → 矩阵行索引}
    movie_map = {} # {电影ID → 矩阵列索引}
    matrix = sparse_matrix()
    
    for rating in CrawledRating.query.all():
        uid = get_or_create(user_map, rating.user_name)
        mid = get_or_create(movie_map, rating.movie_id)
        matrix[uid, mid] = rating.score
    
    for rating in UserRating.query.all():
        uid = get_or_create(user_map, f"user_{rating.user_id}")
        mid = get_or_create(movie_map, rating.movie_id)
        matrix[uid, mid] = rating.score
    
    # 步骤2: NMF 分解
    n_components = min(20, len(movie_map)-1, len(user_map)-1)
    model = NMF(
        n_components=n_components,
        init="nndsvda",
        max_iter=300,
        random_state=42
    )
    U = model.fit_transform(matrix)   # 用户特征矩阵
    V = model.components_.T            # 物品特征矩阵
    
    # 步骤3: 预测评分
    user_idx = user_map.get(f"user_{user_id}")
    predicted = U[user_idx] @ V.T     # 矩阵乘法
    
    # 步骤4: 过滤与排序
    rated_movies = {r.movie_id for r in UserRating.query.filter_by(user_id=user_id)}
    candidates = [
        (mid, score) 
        for mid, score in enumerate(predicted)
        if mid not in rated_movies
    ]
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    # 步骤5: 获取电影详情
    top_movie_ids = [list(movie_map.keys())[mid] for mid, _ in candidates[:limit*2]]
    movies = get_movies_by_ids(top_movie_ids)
    
    return movies[:limit]
```

### 4.3 在线混合推荐伪代码

**文件**：[recommendation_service.py](services/recommendation_service.py) - `_online_hybrid_recommendations()`

```python
# 输入: user_id(int) - 用户ID, rating_count(int) - 用户评分数量
# 输出: dict - 混合推荐结果

def _online_hybrid_recommendations(user_id, rating_count):
    # 1. 获取用户已评分电影
    rated_movie_ids = {str(r.movie_id) for r in UserRating.query.filter_by(user_id=user_id)}
    
    # 2. 并行计算三种算法得分（归一化）
    als_scores = _online_als_scores(user_id, rated_movie_ids)      # ALS 得分
    graphx_scores = _online_graphx_scores(user_id, rated_movie_ids) # GraphX 得分
    content_scores = _content_recommendations_for_user(user_id, rated_movie_ids) # TF-IDF 得分
    
    # 3. 加权融合
    fused_scores = {}
    for movie_id in als_scores:
        fused_scores[movie_id] = (
            als_scores.get(movie_id, 0) * 0.7 +
            graphx_scores.get(movie_id, 0) * 0.2 +
            content_scores.get(movie_id, 0) * 0.1
        )
    
    # 4. 排序与返回
    sorted_movies = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    top_movie_ids = [mid for mid, _ in sorted_movies[:20]]
    
    return {
        "hybrid_items": get_movies_by_ids(top_movie_ids),
        "als_items": get_movies_by_ids([mid for mid, _ in sorted(als_scores.items(), key=lambda x: x[1], reverse=True)[:12]]),
        "graphx_items": get_movies_by_ids([mid for mid, _ in sorted(graphx_scores.items(), key=lambda x: x[1], reverse=True)[:12]]),
        "content_items": get_movies_by_ids([mid for mid, _ in sorted(content_scores.items(), key=lambda x: x[1], reverse=True)[:12]]),
        "strategy": "online_hybrid"
    }
```

---

## 五、子系统跨模块调用关系

### 5.1 调用关系图

```
┌─────────────────────────────────────────────────────────────────┐
│                         app.py（API层）                         │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐      │
│  │ 用户认证路由 │ │ 电影数据路由 │ │   推荐系统路由       │      │
│  └──────┬──────┘ └───────┬──────┘ └──────────┬──────────┘      │
│         │                │                   │                 │
│         ▼                ▼                   ▼                 │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────────────┐      │
│  │   models.py │ │movie_service │ │recommendation_      │      │
│  │ (SQLite ORM)│ │.py           │ │service.py           │      │
│  └─────────────┘ └───────┬──────┘ └──────────┬──────────┘      │
│                          │                   │                 │
│                          ▼                   ▼                 │
│                    ┌──────────┐    ┌───────────────────┐       │
│                    │  MySQL   │    │ recommend_service │       │
│                    │ (movies) │    │ .py               │       │
│                    └──────────┘    │ (NMF-ALS算法)     │       │
│                                    └───────────────────┘       │
│                                              │                 │
│                                              ▼                 │
│                                    ┌───────────────────┐       │
│                                    │  Spark VM Client   │       │
│                                    │ (离线批处理)       │       │
│                                    └───────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 跨模块调用接口表

| 调用方 | 被调用方 | 接口/函数 | 文件路径 |
|--------|----------|-----------|----------|
| app.py | movie_service.py | `get_movie_by_id(movie_id)` | [services/movie_service.py](services/movie_service.py) |
| app.py | movie_service.py | `list_movies(...)` | [services/movie_service.py](services/movie_service.py) |
| app.py | recommendation_service.py | `hybrid_recommendations(user_id)` | [services/recommendation_service.py](services/recommendation_service.py) |
| app.py | analytics_service.py | `overview_stats(...)` | [services/analytics_service.py](services/analytics_service.py) |
| recommendation_service.py | recommend_service.py | `recommend_als_for_user(user_id, limit)` | [services/recommend_service.py](services/recommend_service.py) |
| recommendation_service.py | movie_service.py | `get_movies_by_ids(movie_ids)` | [services/movie_service.py](services/movie_service.py) |
| recommendation_service.py | movie_service.py | `get_home_popular_items(limit)` | [services/movie_service.py](services/movie_service.py) |
| analytics_service.py | movie_service.py | `get_mysql()` | [services/movie_service.py](services/movie_service.py) |
| recommendation_service.py | spark_vm_client.py | `run_spark_pipeline_on_vm()` | [services/spark_vm_client.py](services/spark_vm_client.py) |

### 5.3 推荐系统跨模块调用流程

```
用户访问 /api/recommend/personal
        │
        ▼
app.py → hybrid_recommendations(user_id)
                │
                ├── recommend_service.py: recommend_als_for_user()
                │       ├── models.py: CrawledRating.query.all()
                │       ├── models.py: UserRating.query.all()
                │       └── movie_service.py: get_movies_by_ids()
                │
                ├── recommend_service.py: recommend_graphx_for_user()
                │       └── movie_service.py: get_movies_by_ids()
                │
                ├── recommend_service.py: recommend_content_for_user()
                │       └── movie_service.py: get_movies_by_ids()
                │
                └── movie_service.py: get_home_popular_items()（冷启动兜底）
```

---

## 六、关键函数功能说明

### 6.1 推荐系统核心函数

| 函数 | 文件 | 功能 |
|------|------|------|
| `hybrid_recommendations(user_id)` | [recommendation_service.py](services/recommendation_service.py) | 推荐入口，判断冷启动/正常推荐，选择在线/离线路径 |
| `_online_hybrid_recommendations(user_id, rating_count)` | [recommendation_service.py](services/recommendation_service.py) | 在线混合推荐，融合三种算法得分 |
| `_spark_hybrid_recommendations(user_id, rating_count)` | [recommendation_service.py](services/recommendation_service.py) | 加载 Spark 离线推荐结果并融合 |
| `recommend_als_for_user(user_id, limit)` | [recommend_service.py](services/recommend_service.py) | NMF-ALS 协同过滤推荐（核心算法） |
| `recommend_graphx_for_user(user_id, limit)` | [recommend_service.py](services/recommend_service.py) | GraphX 图相似推荐 |
| `recommend_content_for_user(user_id, limit)` | [recommend_service.py](services/recommend_service.py) | TF-IDF 内容相似推荐 |
| `get_cold_start_movies(limit)` | [recommendation_service.py](services/recommendation_service.py) | 获取热门电影（冷启动兜底） |

### 6.2 电影数据服务函数

| 函数 | 文件 | 功能 |
|------|------|------|
| `get_movie_by_id(movie_id)` | [movie_service.py](services/movie_service.py) | 根据电影ID获取电影详情（MySQL直查） |
| `get_movies_by_ids(movie_ids)` | [movie_service.py](services/movie_service.py) | 批量获取电影详情 |
| `list_movies(...)` | [movie_service.py](services/movie_service.py) | 电影列表查询（分页/筛选/排序） |
| `get_home_sections()` | [movie_service.py](services/movie_service.py) | 获取首页电影区块 |
| `get_similar_movies(movie_id)` | [movie_service.py](services/movie_service.py) | 获取相似电影 |
| `search_suggest(keyword)` | [movie_service.py](services/movie_service.py) | 搜索建议 |
| `get_mysql()` | [movie_service.py](services/movie_service.py) | 获取 MySQL 连接上下文管理器 |

### 6.3 数据分析服务函数

| 函数 | 文件 | 功能 |
|------|------|------|
| `overview_stats(...)` | [analytics_service.py](services/analytics_service.py) | 概览统计（电影数、用户数、评分数） |
| `genre_distribution(...)` | [analytics_service.py](services/analytics_service.py) | 类型分布统计 |
| `country_distribution(...)` | [analytics_service.py](services/analytics_service.py) | 国家分布统计 |
| `rating_distribution(...)` | [analytics_service.py](services/analytics_service.py) | 评分区间分布 |
| `rating_leaderboard(...)` | [analytics_service.py](services/analytics_service.py) | 评分排行榜 |
| `wordcloud_data(...)` | [analytics_service.py](services/analytics_service.py) | 词云数据 |
| `_parse_filters(...)` | [analytics_service.py](services/analytics_service.py) | 解析筛选参数为 SQL WHERE 条件 |

---

## 七、数据预处理流程

### 7.1 数据源

| 数据源 | 文件 | 记录数 |
|--------|------|--------|
| 豆瓣电影 | `19_20.csv` | ~1500条 |
| TMDb | `2015.csv`~`25_26.csv` | ~5200条 |

### 7.2 预处理步骤

**脚本**：[scripts/clean_movies.py](scripts/clean_movies.py)（PySpark）

1. **字段重命名**：中文列名 → 英文列名（共 22 个字段）
2. **空值过滤**：删除 `movie_id` 或 `title` 为空的记录
3. **繁简转换**：使用 OpenCC 将繁体字转换为简体字
4. **多值字段标准化**：`directors`、`actors`、`genres` 等使用 `|` 分隔
5. **类型转换**：`rating(Float)`、`rating_count(Integer)`、`release_year(Integer)`
6. **默认值填充**：`aliases` 为空填"未知"，`awards` 为空填"无"

### 7.3 评分提取

**脚本**：[scripts/extract_ratings.py](scripts/extract_ratings.py)

- 从评论文本中提取用户评分
- 每条评论格式：`[评论N]作者:xxx|评分:x.x/10 评论内容`
- 提取结果：约 33830 条评分数据

---

## 八、老师常问问题

### Q1：为什么用双数据库？

**答**：movies 表数据量大（6766条），包含长文本字段，需要 MySQL 的全文检索和高性能查询能力；用户相关表数据量小，使用 SQLite 开发更快速方便。

### Q2：movies 表的结构在哪里定义？

**答**：不在 [models.py](models.py) 中定义，而是通过 [movies_backup.sql](../../../movies_backup.sql) SQL 备份文件导入 MySQL，由 [movie_service.py](services/movie_service.py) 使用 PyMySQL 直接查询。

### Q3：推荐算法为什么用混合策略？

**答**：单一算法有局限性——协同过滤存在冷启动问题，内容推荐无法发现用户潜在兴趣，图推荐效果不稳定。混合策略（ALS×0.7 + GraphX×0.2 + Content×0.1）可以互补优势，提升推荐质量。

### Q4：冷启动如何处理？

**答**：当用户评分数量 < 3 时，返回热门电影列表（基于评分和评价人数综合排序），用户评分达到 3 条后自动切换为个性化推荐。

### Q5：Spark 离线推荐如何集成？

**答**：用户点击"刷新推荐"时，后端通过 [spark_vm_client.py](services/spark_vm_client.py) 调用 Ubuntu VM 上的 Spark 批处理任务，计算完成后通过 `/api/spark/load-results` 导入推荐结果。

### Q6：前后端如何通信？

**答**：前端 Vue3 通过 Axios 调用 Flask API，开发模式下通过 Vite 代理到后端端口 5000，生产模式下前端打包后由 Flask 统一提供静态文件和 API。

---

## 九、系统架构总结

```
┌─────────────────────────────────────────────────────────┐
│                    前端层（Vue3）                         │
│  HomeView │ MovieDetail │ RecommendView │ AnalyticsView │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP/JSON
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    API层（Flask）                         │
│  app.py - 50+ API端点，@login_required 认证保护           │
└───────────────────────┬─────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ 服务层      │ │ 服务层      │ │ 服务层      │
│movie_service│ │recommend_   │ │recommendation│
│.py         │ │service.py   │ │_service.py  │
└──────┬──────┘ └──────┬──────┘ └──────┬──────┘
       │               │               │
       ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   MySQL     │ │   SQLite    │ │   Spark VM  │
│ movies表    │ │ users等表   │ │ 离线计算    │
└─────────────┘ └─────────────┘ └─────────────┘
```

**详细文档**：[movie-system/README.md](../../README.md)