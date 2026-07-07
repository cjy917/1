"""
【首页 H4】首页底部短评展示
路由：GET /api/movies/home/comments → get_home_section_comments
前端：HomeCommentShowcase.vue
"""
from typing import Any

from models import MovieComment, User
from services.movie_service import get_home_sections, parse_crawled_reviews

# 与首页三个横滑栏对应
SECTION_KEYS = ("popular", "top_rated", "latest")


def _format_comment_item(
    *,
    comment_id: str,
    movie_id: int,
    movie_title: str,
    poster_url: str | None,
    username: str,
    score: float | None,
    content: str,
) -> dict[str, Any]:
    """统一前端气泡所需字段结构"""
    return {
        "id": comment_id,
        "movie_id": movie_id,
        "movie_title": movie_title,
        "poster_url": poster_url or f"/api/posters/{movie_id}",
        "username": username,
        "score": round(float(score), 1) if score is not None else None,
        "content": content.strip(),
    }


def _crawled_pool(movies: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    """用户短评不足时，从 MySQL 爬虫 reviews 字段补量"""
    items: list[dict[str, Any]] = []
    for movie in movies:
        for idx, review in enumerate(parse_crawled_reviews(movie.get("reviews"))):
            content = (review.get("content") or "").strip()
            if len(content) < 5:
                continue
            items.append(
                _format_comment_item(
                    comment_id=f"crawled-{movie['movie_id']}-{idx}",
                    movie_id=movie["movie_id"],
                    movie_title=movie.get("title") or "未知电影",
                    poster_url=movie.get("poster_url"),
                    username=review.get("author") or "影迷",
                    score=review.get("rating"),
                    content=content,
                )
            )
            if len(items) >= limit:
                return items
    return items


def get_home_section_comments(limit_per_section: int = 30) -> dict[str, list[dict[str, Any]]]:
    """
    每个首页分区返回短评列表：
    1. 优先 SQLite 用户发表的 MovieComment
    2. 不足 8 条时用爬虫短评填充
    """
    sections = get_home_sections()
    result: dict[str, list[dict[str, Any]]] = {}

    for key in SECTION_KEYS:
        movies = sections.get(key, [])[:15]
        movie_map = {movie["movie_id"]: movie for movie in movies}
        movie_ids = list(movie_map.keys())
        items: list[dict[str, Any]] = []

        # ─── 用户短评（SQLite） ─────────────────────────────────────────────
        if movie_ids:
            rows = (
                MovieComment.query.filter(MovieComment.movie_id.in_(movie_ids))
                .order_by(MovieComment.created_at.desc())
                .limit(limit_per_section)
                .all()
            )
            user_ids = {row.user_id for row in rows}
            users = (
                {user.id: user.username for user in User.query.filter(User.id.in_(user_ids)).all()}
                if user_ids
                else {}
            )

            for row in rows:
                movie = movie_map.get(row.movie_id)
                if not movie:
                    continue
                content = (row.content or "").strip()
                if len(content) < 5:
                    continue
                items.append(
                    _format_comment_item(
                        comment_id=f"user-{row.id}",
                        movie_id=row.movie_id,
                        movie_title=movie.get("title") or "未知电影",
                        poster_url=movie.get("poster_url"),
                        username=users.get(row.user_id, "用户"),
                        score=row.score,
                        content=content,
                    )
                )

        # ─── 爬虫短评兜底 ───────────────────────────────────────────────────
        if len(items) < 8:
            seen_ids = {item["id"] for item in items}
            for extra in _crawled_pool(movies, limit_per_section):
                if extra["id"] in seen_ids:
                    continue
                items.append(extra)
                seen_ids.add(extra["id"])
                if len(items) >= limit_per_section:
                    break

        result[key] = items[:limit_per_section]

    return result
