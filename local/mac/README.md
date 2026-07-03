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
