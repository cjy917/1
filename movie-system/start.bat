@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ===== 安装 Python 依赖 =====
pip install -r backend\requirements.txt

echo ===== 导入 films_data 电影数据 =====
python scripts\import_films_data.py

echo ===== 修复海报路径（豆瓣 p*.webp） =====
python scripts\fix_poster_paths.py

echo ===== 导出评分数据供 Spark 使用 =====
python scripts\export_spark_ratings.py

echo ===== 启动 Web 服务 =====
echo 访问地址: http://127.0.0.1:5000
echo Spark 推荐任务请在 Ubuntu 虚拟机运行: spark/run_spark_jobs.sh
cd backend
python app.py
