#!/bin/bash
# =====================================================================
#  Mac 一键启动脚本（不修改主仓库任何文件，仅本地使用）
#  行为与 Windows 组员的 start-system.bat 对齐：
#    - 先清理 5000/5173 端口上的旧进程
#    - 打开两个独立 Terminal 窗口，分别运行后端和前端
#    - 端口保持团队标准：后端 5000，前端 5173
#
#  用法：
#    chmod +x local/mac/start-mac.sh    # 首次执行需加权限
#    ./local/mac/start-mac.sh
# =====================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PROJECT_DIR="$REPO_ROOT/movie-system"
VENV_PYTHON="$PROJECT_DIR/.venv/bin/python"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"

log() { printf "\033[1;36m[start-mac]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m %s\n" "$*" >&2; }

# ---------- 0. MySQL 检测与自动启动（Mac 本地服务，不涉及主代码） ----------
check_mysql() {
    lsof -iTCP:3306 -sTCP:LISTEN >/dev/null 2>&1
}

if ! check_mysql; then
    log "MySQL 未启动，尝试自动启动..."
    # 优先尝试 brew services（开机自启），失败则用 mysqld_safe 后台临时启动
    if command -v brew >/dev/null 2>&1 && brew services list 2>/dev/null | grep -q "^mysql "; then
        brew services start mysql >/dev/null 2>&1 || true
    fi
    if ! check_mysql; then
        # 兜底：直接 mysqld_safe 后台启动（数据目录在 brew 默认路径）
        MYSQLD_SAFE="$(brew --prefix mysql 2>/dev/null)/bin/mysqld_safe"
        if [ -x "$MYSQLD_SAFE" ]; then
            DATADIR="$(brew --prefix 2>/dev/null)/var/mysql"
            nohup "$MYSQLD_SAFE" --datadir="$DATADIR" >/tmp/mysql-start.log 2>&1 &
            disown
        else
            warn "找不到 mysqld_safe，请手动启动 MySQL"
            warn "  brew services start mysql   # 推荐（开机自启）"
            warn "  或: /opt/homebrew/opt/mysql/bin/mysqld_safe --datadir=/opt/homebrew/var/mysql &"
        fi
    fi
    # 等待最多 12 秒让 MySQL ready
    for i in 1 2 3 4 5 6; do
        sleep 2
        if check_mysql; then
            log "  MySQL 启动完成（端口 3306）"
            break
        fi
    done
    if ! check_mysql; then
        warn "MySQL 启动超时，请手动启动后再运行本脚本"
        warn "  brew services start mysql"
        exit 1
    fi
fi

# ---------- 1. 环境检查 ----------
log "环境检查..."
if [ ! -f "$VENV_PYTHON" ]; then
    warn "找不到虚拟环境 $VENV_PYTHON"
    warn "请先创建虚拟环境：cd $PROJECT_DIR && python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt"
    exit 1
fi
if [ ! -f "$FRONTEND_DIR/node_modules/.bin/vite" ]; then
    warn "前端依赖未安装，请执行：cd $FRONTEND_DIR && npm install"
    exit 1
fi

# ---------- 2. 清理旧进程 ----------
log "清理旧进程（端口 5000 / 5173）..."
for PORT in 5000 5173; do
    PIDS=$(lsof -ti:$PORT 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        log "  端口 $PORT 占用 -> kill $PIDS"
        kill $PIDS 2>/dev/null || true
        sleep 1
        # 强制清理残留
        PIDS=$(lsof -ti:$PORT 2>/dev/null || true)
        [ -n "$PIDS" ] && kill -9 $PIDS 2>/dev/null || true
    fi
done

# ---------- 3. 启动后端（新 Terminal 窗口） ----------
BACKEND_CMD="cd '$BACKEND_DIR' && echo '=== Flask Backend :5000 ===' && '$VENV_PYTHON' app.py"
log "[1/2] 启动后端 -> Terminal 窗口（http://127.0.0.1:5000）"
osascript -e "tell application \"Terminal\"" \
          -e "    do script \"$BACKEND_CMD\"" \
          -e "    set custom title of front window to \"SparkMovie Backend :5000\"" \
          -e "end tell" >/dev/null

# 等后端初始化
sleep 4

# ---------- 4. 启动前端（新 Terminal 窗口） ----------
FRONTEND_CMD="cd '$FRONTEND_DIR' && echo '=== Vite Frontend :5173 ===' && npm run dev"
log "[2/2] 启动前端 -> Terminal 窗口（http://localhost:5173）"
osascript -e "tell application \"Terminal\"" \
          -e "    do script \"$FRONTEND_CMD\"" \
          -e "    set custom title of front window to \"SparkMovie Frontend :5173\"" \
          -e "end tell" >/dev/null

# ---------- 5. 汇总 ----------
sleep 1
echo
echo "================================================================"
echo "  ✅  Mac 端已启动"
echo "  🌐  前端（Vue）:  http://localhost:5173"
echo "  🔌  后端 API :    http://127.0.0.1:5000/api/health"
echo "  🛑  停止服务 :    ./local/mac/stop-mac.sh"
echo "================================================================"
