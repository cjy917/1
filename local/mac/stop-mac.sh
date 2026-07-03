#!/bin/bash
# =====================================================================
#  Mac 一键停止脚本
#  清理 5000（后端） / 5173（前端） 端口上的进程
#
#  用法：
#    chmod +x local/mac/stop-mac.sh   # 首次执行需加权限
#    ./local/mac/stop-mac.sh
# =====================================================================
set -e

log() { printf "\033[1;35m[stop-mac]\033[0m %s\n" "$*"; }

STOPPED=0
for PORT in 5000 5173; do
    PIDS=$(lsof -ti:$PORT 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        NAME=$(lsof -i:$PORT -sTCP:LISTEN -Fcn 2>/dev/null | awk '/^n/ {print substr($0,2); exit}' || echo "unknown")
        log "kill port $PORT (pid=$PIDS, name=$NAME)"
        kill $PIDS 2>/dev/null || true
        sleep 1
        PIDS=$(lsof -ti:$PORT 2>/dev/null || true)
        if [ -n "$PIDS" ]; then
            log "  force kill -9 $PIDS"
            kill -9 $PIDS 2>/dev/null || true
        fi
        STOPPED=$((STOPPED + 1))
    else
        log "port $PORT 没有运行中的进程"
    fi
done

echo
if [ "$STOPPED" -gt 0 ]; then
    echo "✅ 已停止 $STOPPED 个服务"
else
    echo "ℹ️  没有需要停止的服务"
fi
