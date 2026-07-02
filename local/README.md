# 本地开发配置目录

本目录用于存放**因操作系统或个人环境不同**而产生的配置，**不影响**仓库主代码（以 Windows 团队标准为准）。

## 目录说明

| 路径 | 用途 | 是否提交到 Git |
|------|------|----------------|
| `local/mac/` | Mac 开发者本地配置模板与启动脚本 | 模板提交，`.env` 不提交 |
| `local/mac/.env` | 你的个人环境变量（端口、数据库等） | **不提交** |

## 原则

1. **主代码不变**：`movie-system/backend/app.py`、`movie-system/frontend/vite.config.js` 等共享文件保持 Windows 团队标准（后端 `5000`，前端 `5173`）。
2. **Mac 默认与 Windows 一致**：关闭 AirPlay 接收器后，全员继续使用端口 `5000`，无需本地覆盖。
3. **Mac 差异放这里（备用）**：仅当 AirPlay 重新开启、5000 被占用时，才使用 `local/mac/` 副本配置。
4. **虚拟环境不入库**：`.venv/`、`node_modules/` 各自本地创建，已通过 `.gitignore` 忽略。

## Mac 开发者

见 [local/mac/README.md](./mac/README.md)。
