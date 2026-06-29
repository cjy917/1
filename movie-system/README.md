# Spark 电影推荐系统

Vue3 + Flask + MySQL + Spark MLlib 实训项目，TMDB 风格界面。

## 快速启动

### 1. 确保 MySQL 已导入 `movies_backup.sql`

```bash
mysql -u root -p123456 -e "CREATE DATABASE IF NOT EXISTS movies_db;"
mysql -u root -p123456 movies_db < ../movies_backup.sql
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
python app.py
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

或直接双击 `start.bat`。

- 前端：http://127.0.0.1:5173
- 后端：http://127.0.0.1:5000

## 功能模块

| 模块 | 说明 |
|------|------|
| 用户系统 | 注册、登录、评分、收藏 |
| 电影库 | 列表、搜索、多维筛选、详情 |
| 数据分析 | ECharts 类型/年份/评分/演员可视化 |
| 个性化推荐 | Spark MLlib ALS（本地 NMF 回退）+ 图相似推荐 |
| 数据预览 | 爬虫数据与预处理流程展示 |

## Spark 脚本

`spark/` 目录包含可在 Hadoop/Spark 集群运行的 MLlib 与 GraphX 示例脚本，供实训答辩展示。

## 技术栈

- 前端：Vue3、Vite、Element Plus、ECharts、Tailwind CSS
- 后端：Flask、PyMySQL、SQLAlchemy
- 数据：MySQL `movies_db`（6766 部电影）
- 推荐：Spark MLlib ALS + GraphX/Neo4j 图算法思路
