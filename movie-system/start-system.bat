@echo off
chcp 65001 >nul
title FYWZ Movies - 启动服务

echo 正在清理旧进程...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5173 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

echo [1/2] 启动后端 http://127.0.0.1:5000
start "FYWZ Backend" cmd /k "cd /d %~dp0backend && python app.py"

timeout /t 4 /nobreak >nul

echo [2/2] 启动前端 http://localhost:5173
start "FYWZ Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo 已启动，请访问 http://localhost:5173 或 http://127.0.0.1:5000
exit /b 0
