#!/bin/bash

read -s -p "请输入 MySQL root 密码: " MYSQL_PASSWORD
echo ""

echo "正在创建数据库..."
mysql -u root -p"$MYSQL_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS movies_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

echo "正在创建表..."
mysql -u root -p"$MYSQL_PASSWORD" movies_db << 'EOF'
CREATE TABLE IF NOT EXISTS movies (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    movie_id BIGINT NOT NULL,
    title VARCHAR(200) NOT NULL,
    rating FLOAT DEFAULT 0.0,
    rating_count INT DEFAULT 0,
    release_date VARCHAR(50),
    release_year INT DEFAULT 0,
    directors VARCHAR(1000),
    writers VARCHAR(1000),
    actors VARCHAR(2000),
    aliases VARCHAR(1000),
    summary TEXT,
    detail_url VARCHAR(500),
    languages VARCHAR(500),
    genres VARCHAR(500),
    duration VARCHAR(50),
    reviews TEXT,
    countries VARCHAR(500),
    awards VARCHAR(1000),
    review_count INT DEFAULT 0,
    cover_path VARCHAR(200),
    source VARCHAR(20),
    UNIQUE KEY uk_movie_id (movie_id, source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
EOF

echo "正在导入数据..."
spark-submit --jars /tmp/mysql-connector-j-8.0.33.jar ~/films/scripts/import_to_mysql.py "$MYSQL_PASSWORD"

echo "验证结果..."
mysql -u root -p"$MYSQL_PASSWORD" movies_db -e "SELECT COUNT(*) as total_records FROM movies;"