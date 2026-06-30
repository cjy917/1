# Spark 电影推荐系统

Vue3 + Flask + MySQL + Spark MLlib 构建的现代化电影推荐系统，采用 TMDB 风格界面设计，集成用户认证、电影库管理、数据分析可视化、个性化推荐等核心功能。

---

## 📋 目录

- [项目概述](#项目概述)
- [技术栈](#技术栈)
- [目录结构](#目录结构)
- [数据库设计](#数据库设计)
- [后端模块](#后端模块)
- [前端模块](#前端模块)
- [API 接口文档](#api-接口文档)
- [模块协作流程](#模块协作流程)
- [快速启动](#快速启动)
- [配置说明](#配置说明)
- [扩展指南](#扩展指南)

---

## 🎯 项目概述

本系统是一个完整的电影推荐平台，包含以下核心功能：

| 模块 | 功能 | 技术实现 |
|------|------|----------|
| 用户系统 | 注册、登录、评分、收藏、待看列表 | Flask Session + SQLAlchemy |
| 电影库 | 列表浏览、搜索、多维筛选、详情展示 | MySQL + pymysql |
| 数据分析 | 多维度统计分析、ECharts 可视化、词云 | Flask API + Vue3 + ECharts |
| 个性化推荐 | 协同过滤（NMF）、图相似推荐、热门回退 | scikit-learn NMF |
| 视频播放 | 本地视频、远程代理、预告片 | Flask 流媒体 + yt-dlp |

---

## 🛠 技术栈

### 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.5+ | 前端框架 |
| Vite | 8.1+ | 构建工具 |
| Vue Router | 5.1+ | 路由管理 |
| Pinia | 3.0+ | 状态管理 |
| Element Plus | 2.14+ | UI 组件库 |
| ECharts | 6.1+ | 数据可视化 |
| Tailwind CSS | 4.3+ | 样式框架 |

### 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| Flask | 3.0+ | Web 框架 |
| Flask-CORS | 4.0+ | 跨域支持 |
| Flask-SQLAlchemy | 3.1+ | ORM |
| PyMySQL | 1.1+ | MySQL 驱动 |
| scikit-learn | 1.5+ | 推荐算法（NMF） |
| numpy | 2.1+ | 数值计算 |

### 数据与大数据
| 技术 | 用途 |
|------|------|
| MySQL 8.0+ | 主数据库（6766 部电影） |
| Spark MLlib | 分布式推荐算法（ALS） |
| GraphX / Neo4j | 图相似推荐（设计思路） |

---

## 📁 目录结构

```
movie-system/
├── backend/                    # 后端 Flask 应用
│   ├── services/               # 业务服务层
│   │   ├── analytics_service.py    # 数据分析服务（统计分析、图表数据）
│   │   ├── movie_service.py        # 电影数据服务（CRUD、搜索、筛选）
│   │   ├── recommend_service.py    # 推荐服务（协同过滤、图相似）
│   │   ├── video_service.py        # 视频播放服务（正片、代理）
│   │   ├── trailer_service.py      # 预告片服务（下载、解析）
│   │   ├── poster_theme_service.py # 海报主题服务（颜色提取）
│   │   ├── country_utils.py        # 国家名称规范化工具
│   │   ├── language_utils.py       # 语言名称规范化工具
│   │   ├── archive_service.py      # 归档服务（数据导入）
│   │   ├── tmdb_meta.py            # TMDb 元数据服务
│   │   └── __init__.py
│   ├── app.py                  # Flask 应用入口（路由定义）
│   ├── config.py               # 配置文件（数据库、路径等）
│   ├── models.py               # SQLAlchemy 模型定义
│   └── requirements.txt        # Python 依赖
│
├── frontend/                   # 前端 Vue 应用
│   ├── src/
│   │   ├── analytics/          # 数据分析模块
│   │   │   ├── services/          # API 服务封装
│   │   │   │   └── analytics.js
│   │   │   ├── composables/       # Vue 组合式函数
│   │   │   │   ├── useAnalytics.js
│   │   │   │   └── useChartLinkage.js
│   │   │   └── components/        # 可视化组件
│   │   │       ├── charts/            # 图表组件（PieChart, BarChart 等）
│   │   │       ├── Dashboard/         # 仪表盘组件
│   │   │       └── Common/            # 公共组件（FilterBar 等）
│   │   ├── views/              # 页面视图
│   │   │   ├── HomeView.vue          # 首页
│   │   │   ├── MoviesView.vue        # 电影列表页
│   │   │   ├── MovieDetailView.vue   # 电影详情页
│   │   │   ├── AnalyticsView.vue     # 数据分析页
│   │   │   ├── RecommendView.vue     # 推荐页
│   │   │   ├── ProfileView.vue       # 个人中心
│   │   │   └── AuthView.vue          # 登录注册页
│   │   ├── components/         # 公共组件
│   │   ├── router/             # 路由配置
│   │   ├── stores/             # Pinia 状态管理
│   │   ├── api/                # 通用 API 封装
│   │   ├── utils/              # 工具函数
│   │   ├── App.vue             # 根组件
│   │   ├── main.js             # 入口文件
│   │   └── style.css           # 全局样式
│   ├── public/                 # 静态资源
│   ├── index.html              # HTML 模板
│   ├── vite.config.js          # Vite 配置
│   └── package.json            # 前端依赖
│
├── scripts/                    # 数据处理脚本
│   ├── clean_movies.py         # 数据清洗
│   ├── import_to_mysql.py      # MySQL 导入
│   ├── import_to_neo4j.py      # Neo4j 导入
│   ├── extract_ratings.py      # 评分提取
│   ├── movie_recommendation.py # 推荐算法示例
│   └── download_home_trailers.py # 预告片下载
│
├── spark/                      # Spark 大数据脚本
│   └── movie_recommend_als.py  # Spark MLlib ALS 推荐
│
├── start-system.bat            # Windows 一键启动
├── start-system.ps1            # PowerShell 一键启动
└── README.md                   # 项目说明
```

---

## 🗄 数据库设计

### 用户相关表

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `users` | 用户信息 | id, username, email, password_hash |
| `user_ratings` | 用户评分 | user_id, movie_id, score |
| `favorites` | 收藏列表 | user_id, movie_id |
| `watchlists` | 待看列表 | user_id, movie_id |
| `user_list_items` | 片单 | user_id, movie_id |
| `movie_comments` | 评论 | user_id, movie_id, content, score |

### 数据缓存表

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `crawled_ratings` | 爬取的评分数据 | user_name, movie_id, score |
| `recommendation_cache` | 推荐结果缓存 | user_id, movie_id, score |
| `poster_cache` | 海报 URL 缓存 | movie_id, poster_url |
| `playback_cache` | 播放源缓存 | movie_id, video_url, trailer_key |

### 电影数据表（MySQL）

电影数据存储在 `movies` 表中（由 `movies_backup.sql` 导入），包含约 6766 部电影：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| movie_id | BIGINT | 电影唯一标识 |
| title | VARCHAR | 中文标题 |
| rating | FLOAT | 评分（10分制） |
| rating_count | INT | 评分人数 |
| release_date | DATE | 上映日期 |
| release_year | INT | 上映年份 |
| directors | VARCHAR | 导演（竖线分隔） |
| actors | VARCHAR | 主演（竖线分隔） |
| genres | VARCHAR | 类型（竖线分隔） |
| countries | VARCHAR | 国家（竖线分隔） |
| languages | VARCHAR | 语言（竖线分隔） |
| duration | VARCHAR | 时长 |
| summary | TEXT | 简介 |
| reviews | TEXT | 评论内容 |
| awards | VARCHAR | 获奖信息 |
| cover_path | VARCHAR | 封面路径 |

---

## 🚀 后端模块

### 1. 应用入口 - app.py

Flask 应用主入口，负责：
- 路由注册（约 50+ 个 API 端点）
- 请求参数解析
- 跨域配置
- 登录认证中间件
- 前端静态资源服务

**关键设计**：使用闭包函数 `create_app()` 实现应用工厂模式，便于测试和扩展。

### 2. 电影服务 - movie_service.py

核心数据服务，提供：
- MySQL 连接管理（`get_mysql()` 上下文管理器）
- 电影 CRUD 操作（`list_movies`, `get_movie_by_id`, `get_movies_by_ids`）
- 搜索功能（`search_suggest`）
- 海报解析（`resolve_poster_file`）
- 多值字段解析（`split_pipe`）

### 3. 数据分析服务 - analytics_service.py

数据分析核心引擎，提供 20+ 统计分析函数：

**单维度统计**：
- `genre_distribution()` - 类型分布
- `year_distribution()` - 年份分布
- `country_distribution()` - 国家分布
- `language_distribution()` - 语言分布
- `rating_distribution()` - 评分区间分布
- `duration_distribution()` - 时长分布
- `director_distribution()` - 导演分布
- `actor_distribution()` - 演员分布

**关联分析**：
- `country_genre_correlation()` - 国家-类型关联
- `rating_duration_correlation()` - 评分-时长相关性（散点图）

**特殊功能**：
- `overview_stats()` - 数据概览
- `top_movies()` - 高分电影
- `wordcloud_data()` - 词云数据
- `analytics_filter_options()` - 筛选选项

### 4. 推荐服务 - recommend_service.py

推荐算法实现：

**算法层级**：
1. **协同过滤（NMF）** - `recommend_als_for_user()`
   - 使用 scikit-learn NMF 分解用户-评分矩阵
   - 融合爬取评分和站点评分
2. **内容相似推荐** - `_content_based_for_user()`
   - 基于类型、导演、演员的相似性
3. **热门回退** - `_fallback_popular()`
   - 按热度排序的热门电影

**图相似推荐**：
- `recommend_graph_similar()` - 基于 GraphX/Neo4j 思路的图关系推荐

### 5. 视频服务 - video_service.py

视频播放支持：
- `resolve_playback()` - 解析播放源
- `get_local_video_path()` - 获取本地视频路径
- `pick_remote_url()` - 选择远程播放 URL
- `proxy_video_stream()` - 代理远程视频流

### 6. 工具服务

| 工具 | 功能 |
|------|------|
| `country_utils.py` | 国家名称规范化（处理别名、中英文映射） |
| `language_utils.py` | 语言名称规范化 |
| `poster_theme_service.py` | 海报主题色提取 |

---

## 🎨 前端模块

### 页面视图

| 页面 | 路径 | 功能 |
|------|------|------|
| HomeView | `/` | 首页（Hero 轮播、热门电影、推荐） |
| MoviesView | `/movies` | 电影列表（搜索、多维筛选） |
| MovieDetailView | `/movie/:id` | 电影详情（评分、评论、播放） |
| AnalyticsView | `/analytics` | 数据分析（可视化图表、筛选） |
| RecommendView | `/recommend` | 个性化推荐页 |
| ProfileView | `/profile` | 个人中心（评分、收藏、片单） |
| AuthView | `/login`, `/register` | 登录注册 |

### 数据分析子模块

**API 服务** - `analytics.js`：封装所有 `/api/analytics/*` 接口（16+ 方法）

**状态管理** - `useAnalytics.js`：
- 模块级缓存（避免重复请求）
- 并行数据加载（16+ 请求并行）
- 筛选状态管理

**图表组件**：
| 组件 | 图表类型 | 用途 |
|------|----------|------|
| PieChart | 饼图 | 分布统计（类型、国家、语言等） |
| BarChart | 柱状图 | 排行统计（导演、演员、评分等） |
| LineChart | 折线图 | 趋势分析（年度上映） |
| ScatterChart | 散点图 | 相关性分析（评分-时长） |
| TagCloudSphere | 词云 | 类型标签可视化 |

### 状态管理（Pinia）

| Store | 用途 |
|-------|------|
| `stores/user.js` | 用户认证状态 |
| `stores/ratings.js` | 评分相关状态 |
| `stores/theme.js` | 主题切换状态 |

---

## 🔌 API 接口文档

### 1. 认证接口

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| POST | `/api/auth/logout` | 用户登出 |
| GET | `/api/auth/me` | 获取当前用户 |

### 2. 电影接口

| 方法 | 路径 | 功能 | 参数 |
|------|------|------|------|
| GET | `/api/movies` | 电影列表 | page, page_size, genre, year, keyword, sort |
| GET | `/api/movies/home` | 首页数据 | - |
| GET | `/api/movies/<id>` | 电影详情 | - |
| GET | `/api/movies/<id>/similar` | 相似电影 | - |
| GET | `/api/movies/<id>/trailer` | 预告片 | refresh, autoplay |
| GET | `/api/movies/<id>/play` | 播放源 | quality |
| GET | `/api/movies/filters` | 筛选选项 | - |
| GET | `/api/movies/search` | 搜索建议 | q |

### 3. 用户操作接口

| 方法 | 路径 | 功能 | 认证 |
|------|------|------|------|
| POST/DELETE | `/api/ratings` | 评分/取消评分 | ✅ |
| GET/POST/DELETE | `/api/favorites` | 收藏管理 | ✅ |
| GET/POST/DELETE | `/api/watchlist` | 待看管理 | ✅ |
| GET/POST/DELETE | `/api/lists` | 片单管理 | ✅ |
| GET | `/api/user/ratings` | 我的评分 | ✅ |
| GET | `/api/movies/<id>/comments` | 电影评论 | - |
| POST/DELETE | `/api/comments` | 发表/删除评论 | ✅ |

### 4. 数据分析接口

| 方法 | 路径 | 功能 | 参数 |
|------|------|------|------|
| GET | `/api/analytics/overview` | 数据概览 | genre, year, country |
| GET | `/api/analytics/genres` | 类型分布 | limit, genre, year, country |
| GET | `/api/analytics/years` | 年份分布 | genre, year, country |
| GET | `/api/analytics/countries` | 国家分布 | limit, genre, year, country |
| GET | `/api/analytics/ratings` | 评分分布 | genre, year, country |
| GET | `/api/analytics/languages` | 语言分布 | limit, genre, year, country |
| GET | `/api/analytics/duration` | 时长分布 | genre, year, country |
| GET | `/api/analytics/directors` | 导演分布 | limit, genre, year, country |
| GET | `/api/analytics/actors` | 演员分布 | limit, genre, year, country |
| GET | `/api/analytics/reviews` | 影评分布 | genre, year, country |
| GET | `/api/analytics/awards` | 获奖分布 | limit, genre, year, country |
| GET | `/api/analytics/monthly` | 月度上映 | genre, year, country |
| GET | `/api/analytics/top` | 热门电影 | limit, genre, year, country |
| GET | `/api/analytics/featured` | 精选电影 | limit, genre, year, country |
| GET | `/api/analytics/movies` | 电影列表（导出） | limit, genre, year, country |
| GET | `/api/analytics/country-genre` | 国家-类型关联 | limit, genre, year, country |
| GET | `/api/analytics/rating-duration` | 评分-时长相关性 | genre, year, country |
| GET | `/api/analytics/wordcloud` | 词云数据 | limit, genre, year, country |
| GET | `/api/analytics/filter-options` | 筛选选项 | genre_limit, country_limit |
| GET | `/api/analytics/sources` | 来源分布 | - |
| GET | `/api/analytics/rating-leaderboard` | 评分排行榜 | limit |

### 5. 推荐接口

| 方法 | 路径 | 功能 | 认证 |
|------|------|------|------|
| GET | `/api/recommend/personal` | 个性化推荐 | ✅ |
| POST | `/api/recommend/refresh` | 刷新推荐 | ✅ |
| GET | `/api/recommend/similar/<id>` | 相似推荐 | - |
| GET | `/api/recommend/guest` | 游客推荐 | - |

### 6. 媒体接口

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/posters/<id>` | 获取海报 |
| GET | `/api/videos/<id>` | 视频流 |
| GET | `/api/trailers/<id>` | 预告片流 |
| GET | `/api/trailers/local-ids` | 本地预告片 ID |

### 7. 管理接口

| 方法 | 路径 | 功能 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/admin/data-preview` | 数据预览 |

---

## 🔗 模块协作流程

### 完整数据流图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          前端 (Vue3)                                    │
├─────────────────────────────────────────────────────────────────────────┤
│  App.vue                                                                 │
│    │                                                                     │
│    ├── Router (vue-router)                                              │
│    │     ├── HomeView → 首页数据                                        │
│    │     ├── MoviesView → 电影列表                                      │
│    │     ├── MovieDetailView → 电影详情                                 │
│    │     ├── AnalyticsView → 数据分析                                   │
│    │     ├── RecommendView → 推荐页面                                   │
│    │     ├── ProfileView → 个人中心                                     │
│    │     └── AuthView → 登录注册                                        │
│    │                                                                     │
│    ├── Pinia Stores                                                     │
│    │     ├── user.js → 用户状态                                         │
│    │     ├── ratings.js → 评分状态                                      │
│    │     └── theme.js → 主题状态                                        │
│    │                                                                     │
│    └── Composables                                                      │
│          ├── useAnalytics.js → 数据分析状态管理                          │
│          └── useChartLinkage.js → 图表联动                               │
│                                                                         │
│                              ↓ HTTP (Axios)                             │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                          后端 (Flask)                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  app.py                                                                 │
│    │                                                                     │
│    ├── 路由层 (50+ endpoints)                                           │
│    │     ├── /api/auth/* → 认证                                         │
│    │     ├── /api/movies/* → 电影                                       │
│    │     ├── /api/analytics/* → 数据分析                                │
│    │     ├── /api/recommend/* → 推荐                                    │
│    │     ├── /api/ratings/* → 评分                                      │
│    │     ├── /api/favorites/* → 收藏                                    │
│    │     └── /api/posters/* → 海报                                      │
│    │                                                                     │
│    └── 服务层 (services/)                                               │
│          ├── movie_service.py        → MySQL 数据访问                    │
│          ├── analytics_service.py    → 统计分析逻辑                      │
│          ├── recommend_service.py    → 推荐算法                          │
│          ├── video_service.py        → 视频播放                          │
│          ├── trailer_service.py      → 预告片                            │
│          ├── poster_theme_service.py → 海报主题                          │
│          ├── country_utils.py        → 国家规范化                        │
│          └── language_utils.py       → 语言规范化                        │
│                                                                         │
│                              ↓ MySQL / SQLite                            │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                           数据库                                        │
├─────────────────────────────────────────────────────────────────────────┤
│  MySQL (movies_db)                                                      │
│    ├── movies          → 电影主数据 (6766部)                            │
│    ├── users           → 用户信息                                       │
│    ├── user_ratings    → 用户评分                                       │
│    ├── favorites       → 收藏列表                                       │
│    ├── watchlists      → 待看列表                                       │
│    ├── movie_comments  → 评论                                          │
│    ├── crawled_ratings → 爬取评分 (33830条)                             │
│    ├── recommendation_cache → 推荐缓存                                  │
│    └── playback_cache  → 播放源缓存                                     │
│                                                                         │
│  SQLite (app.db)                                                        │
│    └── 同上（开发环境回退）                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 数据分析流程

```
用户进入 /analytics
    │
    ▼
AnalyticsView.vue 挂载
    │
    ├──→ useAnalytics.loadAllData()
    │       │
    │       ├──→ loadFilterOptions() → /api/analytics/filter-options
    │       │
    │       └──→ fetchDashboard()
    │               │
    │               ├──→ 并行请求 16+ API：
    │               │     ├── /api/analytics/overview
    │               │     ├── /api/analytics/genres
    │               │     ├── /api/analytics/years
    │               │     ├── /api/analytics/countries
    │               │     ├── /api/analytics/ratings
    │               │     ├── /api/analytics/languages
    │               │     ├── /api/analytics/duration
    │               │     ├── /api/analytics/directors
    │               │     ├── /api/analytics/actors
    │               │     ├── /api/analytics/reviews
    │               │     ├── /api/analytics/awards
    │               │     ├── /api/analytics/monthly
    │               │     ├── /api/analytics/top
    │               │     ├── /api/analytics/featured
    │               │     ├── /api/analytics/country-genre
    │               │     ├── /api/analytics/rating-duration
    │               │     └── /api/analytics/wordcloud
    │               │
    │               └──→ 更新响应式状态
    │
    └──→ 图表组件渲染（ECharts）
```

### 推荐流程

```
用户登录后访问 /recommend
    │
    ▼
前端请求 /api/recommend/personal
    │
    ▼
后端 recommend_service.get_cached_recommendations(user_id)
    │
    ├── 有缓存 → 返回缓存结果
    │
    └── 无缓存 → refresh_user_recommendations(user_id)
            │
            ├──→ recommend_als_for_user(user_id)
            │       │
            │       ├──→ _build_rating_matrix()
            │       │     ├── 合并 crawled_ratings（爬取评分）
            │       │     └── 合并 user_ratings（站点评分）
            │       │
            │       ├──→ NMF 分解矩阵
            │       │     ├── n_components = min(20, n_movies-1, n_users-1)
            │       │     └── predicted = user_features @ item_features.T
            │       │
            │       ├──→ 过滤已评分电影
            │       │
            │       └──→ 返回推荐列表
            │
            └──→ 缓存到 recommendation_cache 表
```

### 电影播放流程

```
用户点击播放按钮
    │
    ▼
前端请求 /api/movies/<id>/play
    │
    ▼
video_service.resolve_playback(movie)
    │
    ├──→ 检查 playback_cache 缓存
    │
    ├──→ get_local_video_path(movie_id) → 本地视频
    │
    └──→ pick_remote_url(movie_id) → 远程视频
            │
            └──→ proxy_video_stream(url, Range) → 代理流
```

---

## 🚀 快速启动

### 前置条件

1. **MySQL 8.0+** 已安装并运行
2. **Python 3.8+** 和 **Node.js 18+**
3. 导入数据库备份：

```bash
mysql -u root -p123456 -e "CREATE DATABASE IF NOT EXISTS movies_db;"
mysql -u root -p123456 movies_db < ../movies_backup.sql
```

### 方式一：一键启动（Windows）

```bash
# 双击或运行
.\start-system.bat
```

### 方式二：手动启动

#### 启动后端

```bash
cd backend
pip install -r requirements.txt
python app.py
```

后端服务：http://127.0.0.1:5000

#### 启动前端

```bash
cd frontend
npm install --legacy-peer-deps
npm run dev
```

前端服务：http://127.0.0.1:5173

---

## ⚙️ 配置说明

### 后端配置（backend/config.py）

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| MYSQL_HOST | localhost | MySQL 主机 |
| MYSQL_PORT | 3306 | MySQL 端口 |
| MYSQL_USER | root | MySQL 用户 |
| MYSQL_PASSWORD | 123456 | MySQL 密码 |
| MYSQL_DATABASE | movies_db | 数据库名 |
| SECRET_KEY | spark-movie-recommend-2026 | Flask 密钥 |
| DEFAULT_PAGE_SIZE | 20 | 默认分页大小 |
| MAX_PAGE_SIZE | 60 | 最大分页大小 |

### 环境变量覆盖

可通过环境变量或 `secrets.local` 文件覆盖配置：

```bash
# Windows
set MYSQL_HOST=localhost
set MYSQL_PASSWORD=your_password

# Linux/macOS
export MYSQL_HOST=localhost
export MYSQL_PASSWORD=your_password
```

或创建 `secrets.local` 文件：

```
TMDB_API_KEY=your_tmdb_api_key
MYSQL_PASSWORD=your_password
```

---

## 🔧 扩展指南

### 添加新的数据分析维度

1. **后端**：在 `analytics_service.py` 中添加新函数
2. **后端**：在 `app.py` 中注册新路由
3. **前端**：在 `analytics.js` 中添加 API 方法
4. **前端**：在 `useAnalytics.js` 中添加状态和加载逻辑
5. **前端**：在 `AnalyticsView.vue` 中添加图表组件

### 添加新页面

1. **前端**：在 `src/views/` 中创建新组件
2. **前端**：在 `src/router/index.js` 中注册路由
3. **后端**（如需）：在 `app.py` 中添加 API 接口

### Spark 集群部署

```bash
# 提交 Spark 推荐任务
spark-submit \
  --master spark://master:7077 \
  --deploy-mode cluster \
  --py-files services.zip \
  spark/movie_recommend_als.py
```

---

## 📊 数据规模

| 数据项 | 数量 |
|--------|------|
| 电影总数 | 6766 部 |
| 爬取评分 | 约 33830 条 |
| 数据来源 | 豆瓣 + TMDb |
| 时间范围 | 2015-2026 年 |

---

## ❓ 常见问题

### Q1：前端无法连接后端？

确保后端已启动，检查 CORS 配置（`app.py` 第 77 行）：
```python
CORS(app, supports_credentials=True, origins=["http://localhost:5173", "http://127.0.0.1:5173"])
```

### Q2：MySQL 连接失败？

检查 `config.py` 中的数据库配置，确保 MySQL 服务正在运行：
```bash
mysql -u root -p123456 movies_db -e "SELECT COUNT(*) FROM movies;"
```

### Q3：推荐结果为空？

推荐系统需要爬取评分数据。首次启动时，后端会自动执行 `seed_crawled_ratings()` 导入评分数据。

### Q4：海报无法显示？

海报文件需放置在以下目录之一（按优先级）：
- `posters/`
- `picture/`
- `picture/output/posters/`
- `films_data/picture/`
- `movie-system/picture/`

---

## 📝 参考文档

- `docs/data_dictionary.md` — 详细数据字典
- `docs/handover_document.md` — 完整交接文档