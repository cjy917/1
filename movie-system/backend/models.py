"""
SQLAlchemy 数据模型定义

【重要说明】
本文件仅定义用户相关的 SQLite 表模型（users、user_ratings、favorites 等）。
电影核心表 `movies` 未在此定义，原因如下：
  1. movies 表数据量大（6766条），字段多（22个），包含长文本字段（summary、reviews）
  2. 需要 MySQL 的全文检索和高性能查询能力
  3. movies 表通过 SQL 备份文件 [movies_backup.sql](../../movies_backup.sql) 导入 MySQL
  4. 由 [movie_service.py](services/movie_service.py) 使用 PyMySQL 直接查询

数据库架构：
├── MySQL（movies表）：6766部电影，22个字段，通过SQL备份导入
└── SQLite（本文件定义）：用户数据，9张表，由SQLAlchemy自动创建
"""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(db.Model):
    """用户表 - 存储系统注册用户信息"""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ratings = db.relationship("UserRating", backref="user", lazy=True)
    favorites = db.relationship("Favorite", backref="user", lazy=True)

    def set_password(self, password: str) -> None:
        """设置密码（自动进行哈希加密）"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """验证密码（比对哈希值）"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        """转换为字典格式（用于API返回）"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserRating(db.Model):
    """用户评分表 - 存储用户对电影的评分记录（0.5-10分）"""
    __tablename__ = "user_ratings"
    __table_args__ = (db.UniqueConstraint("user_id", "movie_id", name="uq_user_movie_rating"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "movie_id": self.movie_id,
            "score": self.score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Favorite(db.Model):
    """收藏表 - 存储用户收藏的电影"""
    __tablename__ = "favorites"
    __table_args__ = (db.UniqueConstraint("user_id", "movie_id", name="uq_user_movie_favorite"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Watchlist(db.Model):
    """待看片单表 - 存储用户标记为待看的电影"""
    __tablename__ = "watchlists"
    __table_args__ = (db.UniqueConstraint("user_id", "movie_id", name="uq_user_movie_watchlist"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserListItem(db.Model):
    """用户片单表 - 默认片单「我的片单」中的电影"""
    __tablename__ = "user_list_items"
    __table_args__ = (db.UniqueConstraint("user_id", "movie_id", name="uq_user_movie_list"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MovieComment(db.Model):
    """电影评论表 - 存储用户发表的电影评论"""
    __tablename__ = "movie_comments"
    __table_args__ = (db.UniqueConstraint("user_id", "movie_id", name="uq_user_movie_comment"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    score = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship("User", backref="movie_comments")

    def to_dict(self, username: str | None = None) -> dict:
        """转换为字典格式（含用户名）"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": username,
            "movie_id": self.movie_id,
            "content": self.content,
            "score": self.score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CrawledRating(db.Model):
    """爬虫评分表 - 从豆瓣/TMDb爬取的用户评分数据（约33830条）"""
    __tablename__ = "crawled_ratings"
    __table_args__ = (db.UniqueConstraint("user_name", "movie_id", name="uq_crawled_rating"),)

    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(120), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(20), default="douban")


class RecommendationCache(db.Model):
    """推荐缓存表 - 在线推荐算法的结果缓存"""
    __tablename__ = "recommendation_cache"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    algorithm = db.Column(db.String(32), default="als")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SparkRecommendation(db.Model):
    """Spark离线推荐结果表 - 存储Spark批处理产出的ALS/GraphX/Content推荐结果"""
    __tablename__ = "spark_recommendations"
    __table_args__ = (
        db.UniqueConstraint("user_id", "movie_id", "algorithm", name="uq_spark_rec"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    algorithm = db.Column(db.String(32), nullable=False, default="als")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self, movie: dict | None = None) -> dict:
        """转换为字典格式（可附带电影信息）"""
        data = {
            "movie_id": self.movie_id,
            "score": round(self.score, 4),
            "algorithm": self.algorithm,
        }
        if movie:
            data.update(
                {
                    "title": movie.get("title"),
                    "poster_url": movie.get("poster_url"),
                    "genres": movie.get("genres"),
                    "rating": movie.get("rating"),
                }
            )
        return data


class PosterCache(db.Model):
    """海报缓存表 - 缓存TMDb海报URL，避免重复请求"""
    __tablename__ = "poster_cache"

    movie_id = db.Column(db.BigInteger, primary_key=True)
    poster_url = db.Column(db.String(512), nullable=False)
    source = db.Column(db.String(20), default="tmdb")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlaybackCache(db.Model):
    """播放缓存表 - 缓存预告片/正片的播放信息"""
    __tablename__ = "playback_cache"

    movie_id = db.Column(db.BigInteger, primary_key=True)
    video_url = db.Column(db.String(512))
    video_source = db.Column(db.String(32))
    trailer_type = db.Column(db.String(16))
    trailer_key = db.Column(db.String(64))
    tmdb_id = db.Column(db.String(32))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


"""
数据库表关系总结：
┌─────────────────────────────────────────────────────────┐
│                      users (1)                          │
├─────────────────────────────────────────────────────────┤
│  1:N  user_ratings      — 用户评分记录                   │
│  1:N  favorites          — 用户收藏记录                   │
│  1:N  watchlists         — 用户待看记录                   │
│  1:N  user_list_items    — 用户片单记录                   │
│  1:N  movie_comments     — 用户评论记录                   │
│  1:N  recommendation_cache — 在线推荐缓存               │
│  1:N  spark_recommendations — Spark离线推荐结果         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                   movies (MySQL，独立)                   │
│  注：通过 movie_id 字段与上述表关联，但无外键约束          │
│  表结构定义在：../../movies_backup.sql                    │
│  查询方式：PyMySQL 直接查询（services/movie_service.py）   │
└─────────────────────────────────────────────────────────┘
"""