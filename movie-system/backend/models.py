from __future__ import annotations

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    ratings = db.relationship("UserRating", backref="user", lazy=True)
    favorites = db.relationship("Favorite", backref="user", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserRating(db.Model):
    __tablename__ = "user_ratings"
    __table_args__ = (db.UniqueConstraint("user_id", "movie_id", name="uq_user_movie_rating"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "movie_id": self.movie_id,
            "score": self.score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Favorite(db.Model):
    __tablename__ = "favorites"
    __table_args__ = (db.UniqueConstraint("user_id", "movie_id", name="uq_user_movie_favorite"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Watchlist(db.Model):
    __tablename__ = "watchlists"
    __table_args__ = (db.UniqueConstraint("user_id", "movie_id", name="uq_user_movie_watchlist"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class UserListItem(db.Model):
    """默认片单「我的片单」中的电影。"""
    __tablename__ = "user_list_items"
    __table_args__ = (db.UniqueConstraint("user_id", "movie_id", name="uq_user_movie_list"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MovieComment(db.Model):
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
    __tablename__ = "crawled_ratings"
    __table_args__ = (db.UniqueConstraint("user_name", "movie_id", name="uq_crawled_rating"),)

    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(120), nullable=False, index=True)
    movie_id = db.Column(db.BigInteger, nullable=False, index=True)
    score = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(20), default="douban")


class PosterCache(db.Model):
    __tablename__ = "poster_cache"

    movie_id = db.Column(db.BigInteger, primary_key=True)
    poster_url = db.Column(db.String(512), nullable=False)
    source = db.Column(db.String(20), default="tmdb")
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PlaybackCache(db.Model):
    __tablename__ = "playback_cache"

    movie_id = db.Column(db.BigInteger, primary_key=True)
    video_url = db.Column(db.String(512))
    video_source = db.Column(db.String(32))
    trailer_type = db.Column(db.String(16))
    trailer_key = db.Column(db.String(64))
    tmdb_id = db.Column(db.String(32))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
