# Vue3 前端项目

Spark 电影推荐系统的前端应用，基于 Vue3 + Vite + Element Plus + ECharts 构建。

## 📋 项目概览

| 模块 | 功能 |
|------|------|
| 首页 | Hero 轮播、热门电影、推荐、预告片播放 |
| 电影列表 | 搜索、多维筛选、排序 |
| 电影详情 | 评分、评论、播放、相似推荐 |
| 数据分析 | 多维度统计、可视化图表、词云 |
| 个性化推荐 | 协同过滤推荐结果 |
| 个人中心 | 评分、收藏、片单管理 |

## 🛠 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.5+ | 前端框架 |
| Vite | 8.1+ | 构建工具 |
| Vue Router | 5.1+ | 路由管理 |
| Pinia | 3.0+ | 状态管理 |
| Element Plus | 2.14+ | UI 组件库 |
| ECharts | 6.1+ | 数据可视化 |
| Tailwind CSS | 4.3+ | 样式框架 |
| Axios | 1.7+ | HTTP 请求 |

## 📁 目录结构

```
frontend/
├── src/
│   ├── analytics/          # 数据分析子模块
│   │   ├── services/       # API 服务封装
│   │   ├── composables/    # Vue 组合式函数
│   │   └── components/     # 可视化组件（图表、仪表盘）
│   ├── views/              # 页面视图（7个页面）
│   ├── components/         # 公共组件
│   ├── router/             # 路由配置
│   ├── stores/             # Pinia 状态管理
│   ├── api/                # 通用 API 封装
│   ├── utils/              # 工具函数
│   ├── App.vue             # 根组件
│   ├── main.js             # 入口文件
│   └── style.css           # 全局样式
├── public/                 # 静态资源
├── index.html              # HTML 模板
├── vite.config.js          # Vite 配置
└── package.json            # 前端依赖
```

## 🚀 快速启动

### 安装依赖

```bash
npm install --legacy-peer-deps
```

> **注意**：由于 ECharts 和 echarts-wordcloud 存在 peer dependency 冲突，需使用 `--legacy-peer-deps` 参数。

### 开发模式

```bash
npm run dev
```

访问：http://localhost:5173

### 生产构建

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

## 🔌 API 接口

前端通过 Axios 调用后端 API，基地址配置在 `src/api/index.js`：

```javascript
const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})
```

主要接口模块：
- `/api/auth/*` - 用户认证
- `/api/movies/*` - 电影数据
- `/api/analytics/*` - 数据分析
- `/api/recommend/*` - 推荐系统
- `/api/posters/*` - 海报资源

## 📊 数据分析模块

数据分析页面位于 `/analytics`，包含：

| 图表组件 | 用途 |
|----------|------|
| PieChart | 分布统计（类型、国家、语言） |
| BarChart | 排行统计（导演、演员、评分） |
| LineChart | 趋势分析（年度上映） |
| ScatterChart | 相关性分析（评分-时长） |
| TagCloudSphere | 类型词云 |

状态管理通过 `composables/useAnalytics.js` 实现，支持并行数据加载和筛选联动。

## 🎬 预告片播放

首页 Hero 轮播支持预告片播放：
- 优先播放本地预告片（`FYWZ/trailers/{movie_id}.mp4`）
- 无本地文件时调用 YouTube 嵌入播放
- 本地预告片通过 `scripts/download_home_trailers.py` 下载

## 📝 开发规范

### 组件命名
- 页面视图：`{Name}View.vue`（如 `HomeView.vue`）
- 公共组件：`{Name}Component.vue`（如 `HeroCarousel.vue`）
- 数据分析组件：`analytics/components/` 下按功能分类

### 代码风格
- 使用 Vue3 `<script setup>` 语法
- 组合式函数放在 `composables/` 目录
- API 服务封装在 `services/` 目录
