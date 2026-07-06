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

## Mac 本地 MySQL 初始化（一次性，与 Windows 组员对齐配置）

> 电影主数据 6766 条存储在 MySQL `movies_db.movies` 表（和 Windows 组员完全一致）。
> 密码 `123456`、数据库名 `movies_db`、主机 `localhost:3306`，与主仓库 `config.py` 完全一致。

### 安装 & 初始化

```bash
# 1. 安装 ARM64 版 MySQL（M5 芯片）
brew install mysql

# 2. 创建并初始化数据目录（brew 默认路径 /opt/homebrew/var/mysql）
mkdir -p /opt/homebrew/var/mysql && chmod 700 /opt/homebrew/var/mysql
/opt/homebrew/opt/mysql/bin/mysqld --initialize-insecure --user=$(whoami) --datadir=/opt/homebrew/var/mysql

# 3. 后台启动 MySQL（若 brew services 有权限，也可用 brew services start mysql）
/opt/homebrew/opt/mysql/bin/mysqld_safe --datadir=/opt/homebrew/var/mysql &

# 4. 设置 root 密码、建库、导入仓库自带备份（就是组员用的那份）
/opt/homebrew/opt/mysql/bin/mysql -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '123456'; FLUSH PRIVILEGES;"
/opt/homebrew/opt/mysql/bin/mysql -u root -p123456 -e "CREATE DATABASE IF NOT EXISTS movies_db DEFAULT CHARACTER SET utf8mb4;"
/opt/homebrew/opt/mysql/bin/mysql -u root -p123456 movies_db < films_data/movies_backup.sql

# 5. 验证（应输出 6766）
/opt/homebrew/opt/mysql/bin/mysql -u root -p123456 movies_db -e "SELECT COUNT(*) FROM movies;"
```

### 日常启动 / 开机自启

两种方式选其一（推荐 `brew services`，能开机自启）：

| 方式 | 命令 | 说明 |
|------|------|------|
| 开机自启（推荐） | `brew services start mysql` | 需要首次手动在**非沙箱终端**执行 |
| 临时后台启动 | `/opt/homebrew/opt/mysql/bin/mysqld_safe --datadir=/opt/homebrew/var/mysql &` | 重启电脑后需要重跑 |

> 🔔 「一键启动脚本」`start-mac.sh` 已内置 MySQL 自动检测：发现 3306 未监听时会自动尝试启动。

---

## 一键启动脚本（推荐，对齐 Windows start-system.bat）

脚本放在 `local/mac/`，不修改主仓库任何文件，行为与 Windows 组员的 `start-system.bat` 完全一致（自动清理旧进程、开独立 Terminal 窗口分别跑前后端）。

```bash
# 首次使用：加执行权限（一次性）
chmod +x local/mac/start-mac.sh local/mac/stop-mac.sh

# 在仓库根目录 GitHub/ 下执行
./local/mac/start-mac.sh
# 脚本会：检查环境 → 清理 5000/5173 旧进程 → 开两个 Terminal 窗口 → 打印访问地址

# 停止服务
./local/mac/stop-mac.sh
```

效果：
- Terminal 窗口标题分别为 `SparkMovie Backend :5000` 和 `SparkMovie Frontend :5173`
- 访问地址：`http://localhost:5173`（与 Windows 组员一致）

---

## 标准启动（手动，与 Windows 相同）

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
| `start-mac.sh` | ✅ **日常使用**：Mac 一键启动脚本（对齐 Windows start-system.bat） |
| `stop-mac.sh` | ✅ **日常使用**：Mac 一键停止脚本（清理 5000/5173 进程） |
| `vite.config.js` | **备用**：AirPlay 开启时前端代理到 5001 |
| `.env.example` | **备用**：本地环境变量模板 |
| `patches/` | 可选的团队级跨平台改进（需协商后合并） |

## 与组员协作

- 提交代码前：`git status` 确认没有 `.venv/`、`.DS_Store`、`local/mac/.env`
- 日常开发：**关闭 AirPlay + 端口 5000**，与 Windows 零差异
- 只提交业务代码，**不要**把 Mac 端口改动写进主配置文件

---

## 🔌 AI 智能语音小助手（硅基流动免费 API）

全局悬浮窗组件，支持**文本/语音输入**与 AI 对话。需要配置免费的 API Key 才能启用对话功能（不配置时组件仍显示，会提示未配置 Key）。

### 获取免费 API Key（5 分钟搞定）

1. 访问 https://cloud.siliconflow.cn/ ，用手机号注册
2. 登录后点击右上角头像 → **「API 密钥」**
3. 点击 **「创建新密钥」** → 输入名字如 `movie-assistant` → 复制生成的 `sk-xxxxxx` 字符串

### 配置方法

编辑 `movie-system/secrets.local`，取消注释并填入：

```
AI_ASSISTANT_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

配置后**重启 Flask 后端**即可生效。

### 功能说明

| 功能 | 说明 |
|------|------|
| 🎤 语音输入 | 基于浏览器 Web Speech API（推荐 Chrome/Edge/Safari） |
| 🔊 朗读回复 | 点击每条 AI 回复旁的 🔈 按钮即可语音播放 |
| 💬 多轮对话 | 自动携带最近 10 轮上下文 |
| 💾 状态持久化 | 悬浮窗状态、对话历史保存在 localStorage，页面切换不丢失 |
| 🗑️ 清空记录 | 悬浮窗头部「垃圾桶」按钮 |

> 🌐 选用硅基流动的原因：**国内无需翻墙**、**每日千万级免费 tokens**、API 兼容 OpenAI 格式、对接极简（Python 标准库 urllib 即可，无需第三方依赖）。

### 🚀 macOS + Shadowrocket 代理用户专属（自动支持动态端口）

如果你用 **Shadowrocket (小火箭)** 作为代理客户端（默认端口不固定）：

1. **打开 Shadowrocket → 顶部开关切到「已连接」**（绿灯）
2. **Shadowrocket 侧边栏 → 设置 → 勾选「设置为系统代理」**
3. 完成！后端会**自动读取 macOS 系统代理设置**（执行 `scutil --proxy`）获取 Shadowrocket 的动态 HTTP/HTTPS/SOCKS 端口，**你不需要手动写死任何端口**。

#### 验证代理是否自动生效

在 Terminal 里执行：
```bash
cd movie-system/backend
source ../.venv/bin/activate
python app.py
# 另开一个浏览器页面，登录后给 AI 小助手发任意消息
```

回到 Flask 运行的 Terminal 窗口，你会看到类似日志：
```
INFO:ai_http_helper:✨ 自动检测到 macOS HTTP 代理: http://127.0.0.1:6xxxxx
INFO:ai_http_helper:✨ 自动检测到 macOS SOCKS 代理: socks5://127.0.0.1:6xxxxx
INFO:ai_http_helper:[SiliconFlow] POST https://api.siliconflow.cn/v1/chat/completions 开始请求 代理=启用(https,http) ...
INFO:ai_http_helper:[SiliconFlow] ... 响应成功 HTTP_200 耗时=1847ms
```

只要看到 `代理=启用(...)` 就说明 Shadowrocket 的动态端口已经被后端自动识别并成功使用。

#### 如果自动识别失败（极少情况）— 手动固定端口兜底

1. Shadowrocket → 首页 → 点击当前节点右侧的 ⓘ 图标
2. 找到「**HTTP 代理**」，开启开关并设一个固定端口，比如 **8888**（保持 Shadowrocket 在后台运行）
3. 编辑 `movie-system/secrets.local`，追加：
   ```
   HTTP_PROXY=http://127.0.0.1:8888
   HTTPS_PROXY=http://127.0.0.1:8888
   ```
4. 重启 Flask 后端即可（本方式永远比自动检测更稳定，推荐常驻使用）。
