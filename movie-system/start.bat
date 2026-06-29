@echo off
chcp 65001 >nul
echo ========================================
echo   Spark 电影推荐系统 - 一键启动
echo ========================================
echo.

echo [1/2] 打包前端页面...
cd /d %~dp0frontend
call npm run build
if errorlevel 1 (
    echo 前端打包失败，请检查是否已执行 npm install
    pause
    exit /b 1
)

echo.
echo [2/2] 启动系统服务...
cd /d %~dp0backend
start "Spark电影推荐系统" cmd /k "python app.py"

echo.
echo 系统地址（只需打开这一个）:
echo   http://127.0.0.1:5000
echo.
timeout /t 3 /nobreak >nul
start http://127.0.0.1:5000
pause
