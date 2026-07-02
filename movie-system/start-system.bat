@echo off
chcp 65001 >nul
title SparkMovie 合并系统 - 启动服务

echo 正在清理旧进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

echo [1/2] 启动后端 http://127.0.0.1:5000
start "SparkMovie Backend" cmd /k "cd /d %~dp0backend && python app.py"

timeout /t 4 /nobreak >nul

echo [2/2] 启动前端 http://localhost:5173
start "SparkMovie Frontend" cmd /k "cd /d %~dp0frontend && npm.cmd run dev"

echo.
echo 合并系统已启动：组员 Vue 前端 + Spark 混合推荐后端
echo 请访问 http://localhost:5173
exit /b 0
