@echo off
chcp 65001 >nul
title SparkMovie 后端（无 Node 时使用）

echo 启动 Flask 后端 http://127.0.0.1:5000
echo 前端使用已打包的 frontend\dist（无需 npm）
echo.
cd /d "%~dp0backend"
python app.py
