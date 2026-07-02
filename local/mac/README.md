# Mac 本地开发指南

## 常见问题：端口 5000 被占用

macOS 的 **AirPlay 接收器** 默认占用 `5000` 端口，可能导致 Flask 后端无法启动。  
**不要**直接修改仓库里的 `app.py` 或 `vite.config.js`，请使用本目录的副本配置。

## 快速开始

### 1. 复制环境变量模板

```bash
cp local/mac/.env.example local/mac/.env
```

按需编辑 `local/mac/.env`（例如 `BACKEND_PORT=5001`）。

### 2. 启动前端（使用 Mac 专用 Vite 配置）

```bash
cd movie-system/frontend
npm run dev -- --config ../../local/mac/vite.config.js
```

Mac 版 Vite 配置将 API 代理指向 `5001` 端口（可在 `vite.config.js` 中修改）。

### 3. 启动后端

**方案 A（推荐，需团队同意改一行主代码）**  
若 `app.py` 支持环境变量 `BACKEND_PORT`（见 `patches/` 中的建议补丁），则：

```bash
cd movie-system/backend
source ../.venv/bin/activate   # 或自行创建的 venv
export $(grep -v '^#' ../../local/mac/.env | xargs)
python app.py
```

**方案 B（不改主代码，临时手动指定）**  
每次启动前手动指定端口（需自行确保与 `local/mac/vite.config.js` 一致）：

```bash
# 仅作示例，当前 app.py 仍写死 5000，需先应用 patches 或与组长协商
BACKEND_PORT=5001 python app.py
```

### 4. 关闭 AirPlay 占用 5000（可选）

系统设置 → 通用 → AirDrop 与隔空播放 → 关闭「隔空播放接收器」，  
之后可直接使用 Windows 标准端口 `5000`，无需本目录覆盖。

## 文件说明

| 文件 | 说明 |
|------|------|
| `vite.config.js` | Mac 前端配置副本（默认代理到 5001） |
| `.env.example` | 环境变量模板 |
| `patches/` | 建议提交给团队的跨平台改进（需协商后再合并到主代码） |

## 与组员协作

- 提交代码前：`git status` 确认没有 `.venv/`、`.DS_Store`、`local/mac/.env`
- 只提交业务代码改动，**不要**提交 Mac 端口修改到主配置文件
- 若团队同意统一用环境变量管理端口，可将 `patches/` 中的改动合并进主分支，Mac/Windows 均受益
