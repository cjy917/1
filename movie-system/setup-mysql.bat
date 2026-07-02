@echo off
chcp 65001 >nul
title 导入 MySQL 电影数据库

set SQL_FILE=d:\作业\大三下\小学期-大数据编程实践\FYWZ\movies_backup.sql
set MYSQL_USER=root
set MYSQL_PWD=123456
set MYSQL_DB=movies_db

REM 自动查找 mysql.exe（优先使用本机已安装的 MySQL 5.7）
set MYSQL_BIN=
if exist "D:\zuoye\dasanxia\mysql-5.7.44-winx64\bin\mysql.exe" set MYSQL_BIN=D:\zuoye\dasanxia\mysql-5.7.44-winx64\bin
if "%MYSQL_BIN%"=="" if exist "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" set MYSQL_BIN=C:\Program Files\MySQL\MySQL Server 8.0\bin
if "%MYSQL_BIN%"=="" if exist "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe" set MYSQL_BIN=C:\Program Files\MySQL\MySQL Server 8.4\bin
if "%MYSQL_BIN%"=="" (
    where mysql >nul 2>&1
    if not errorlevel 1 set MYSQL_BIN=
)

if "%MYSQL_BIN%"=="" (
    where mysql >nul 2>&1
    if errorlevel 1 (
        echo 找不到 mysql 命令。
        echo 请修改本脚本顶部 MYSQL_BIN 变量，指向 mysql.exe 所在 bin 目录
        echo 例如: set MYSQL_BIN=D:\zuoye\dasanxia\mysql-5.7.44-winx64\bin
        pause
        exit /b 1
    )
    set MYSQL_CMD=mysql
) else (
    set MYSQL_CMD="%MYSQL_BIN%\mysql.exe"
    echo 使用 MySQL: %MYSQL_BIN%
)

echo ===== 检查 movies_backup.sql =====
if not exist "%SQL_FILE%" (
    echo 找不到: %SQL_FILE%
    echo 请确认 FYWZ 目录下有 movies_backup.sql
    pause
    exit /b 1
)

echo ===== 创建数据库 %MYSQL_DB% =====
%MYSQL_CMD% -u %MYSQL_USER% -p%MYSQL_PWD% -e "CREATE DATABASE IF NOT EXISTS %MYSQL_DB% DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
if errorlevel 1 (
    echo 创建数据库失败。若密码不是 123456，请修改 backend\config.py 中 MYSQL_PASSWORD
    pause
    exit /b 1
)

echo ===== 导入数据（约 22MB，可能需要 2-5 分钟）=====
%MYSQL_CMD% -u %MYSQL_USER% -p%MYSQL_PWD% %MYSQL_DB% < "%SQL_FILE%"
if errorlevel 1 (
    echo 导入失败，请检查 MySQL 是否在运行
    pause
    exit /b 1
)

echo ===== 验证 =====
%MYSQL_CMD% -u %MYSQL_USER% -p%MYSQL_PWD% -e "USE %MYSQL_DB%; SELECT COUNT(*) AS movie_count FROM movies;"

echo.
echo 完成！请重启后端 python app.py，然后刷新浏览器 http://localhost:5173
pause
