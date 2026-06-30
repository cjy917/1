#!/bin/bash
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "===== 安装 Python 依赖 ====="
pip install -r backend/requirements.txt

echo "===== 导入电影数据 ====="
python scripts/import_data.py

echo "===== 启动 Web 服务 ====="
echo "访问地址: http://127.0.0.1:5000"
cd backend
python app.py
