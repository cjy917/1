# Mac 本地开发指南

## 当前团队方案：关闭 AirPlay，全员使用 5000

Mac 与 Windows **统一使用标准端口**：

| 服务 | 端口 |
|------|------|
| Flask 后端 | `5000` |
| Vite 前端 | `5173` |

无需使用本目录的副本配置，直接按仓库主配置启动即可。

### 关闭 AirPlay（Mac 必做，一次性）

1. 打开 **系统设置**
2. **通用** → **AirDrop 与隔空播放**
3. 关闭 **「隔空播放接收器」**

关闭后 5000 端口释放，与 Windows 组员完全一致。

### 恢复 AirPlay 后怎么办？

随时可以重新打开「隔空播放接收器」。若恢复后 5000 再次被占用，再启用下方 **备用方案**（`local/mac/` 副本配置），**不要**修改主仓库里的 `app.py` 或 `vite.config.js`。

---

## 标准启动（推荐，与 Windows 相同）

```bash
# 后端
cd movie-system/backend
source ../.venv/bin/activate
python app.py

# 前端（另开终端）
cd movie-system/frontend
npm run dev
```

---

## 备用方案：AirPlay 开启时的端口冲突

若无法关闭 AirPlay，或 5000 仍被占用，使用本目录副本（默认改用 `5001`）：

### 1. 复制环境变量

```bash
cp local/mac/.env.example local/mac/.env
# 编辑 .env，设置 BACKEND_PORT=5001
```

### 2. 前端（Mac 副本配置）

```bash
cd movie-system/frontend
npm run dev -- --config ../../local/mac/vite.config.js
```

### 3. 后端

需与团队协商后应用 `patches/` 中的环境变量方案，或临时自行处理端口映射。详见 [patches/README.md](./patches/README.md)。

---

## 文件说明

| 文件 | 说明 |
|------|------|
| `vite.config.js` | **备用**：AirPlay 开启时前端代理到 5001 |
| `.env.example` | **备用**：本地环境变量模板 |
| `patches/` | 可选的团队级跨平台改进（需协商后合并） |

## 与组员协作

- 提交代码前：`git status` 确认没有 `.venv/`、`.DS_Store`、`local/mac/.env`
- 日常开发：**关闭 AirPlay + 端口 5000**，与 Windows 零差异
- 只提交业务代码，**不要**把 Mac 端口改动写进主配置文件
