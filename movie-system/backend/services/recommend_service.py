import csv
from collections import defaultdict
from typing import Any

import numpy as np
from sklearn.decomposition import NMF

from config import RATINGS_CSV
from models import CrawledRating, RecommendationCache, UserRating, db
from services.movie_service import get_movies_by_ids, get_similar_movies, list_movies


def seed_crawled_ratings(force: bool = False) -> int:
    if not force and CrawledRating.query.count() > 0:
        return CrawledRating.query.count()
    if not RATINGS_CSV.exists():
        return 0

    if force:
        CrawledRating.query.delete()
        db.session.commit()

    batch: list[CrawledRating] = []
    with RATINGS_CSV.open("r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            batch.append(
                CrawledRating(
                    user_name=row["user_id"].strip(),
                    movie_id=int(row["movie_id"]),
                    score=float(row["rating"]),
                    source=row.get("source", "douban"),
                )
            )
            if len(batch) >= 1000:
                db.session.bulk_save_objects(batch)
                db.session.commit()
                batch.clear()
    if batch:
        db.session.bulk_save_objects(batch)
        db.session.commit()
    return CrawledRating.query.count()


def _build_rating_matrix() -> tuple[np.ndarray, dict[int, int], dict[int, int], list[int], list[int]]:
    user_map: dict[str, int] = {}
    movie_map: dict[int, int] = {}
    rows: list[tuple[int, int, float]] = []

    for item in CrawledRating.query.all():
        uid = user_map.setdefault(item.user_name, len(user_map))
        mid = movie_map.setdefault(item.movie_id, len(movie_map))
        rows.append((uid, mid, item.score))

    for item in UserRating.query.all():
        uid = user_map.setdefault(f"site_user_{item.user_id}", len(user_map))
        mid = movie_map.setdefault(item.movie_id, len(movie_map))
        rows.append((uid, mid, item.score))

    if not rows:
        return np.array([]), {}, {}, [], []

    n_users = len(user_map)
    n_movies = len(movie_map)
    matrix = np.zeros((n_users, n_movies))
    for uid, mid, score in rows:
        matrix[uid, mid] = score

    inv_user = {v: k for k, v in user_map.items()}
    inv_movie = {v: k for k, v in movie_map.items()}
    return matrix, user_map, movie_map, list(inv_user.keys()), list(inv_movie.values())


def recommend_als_for_user(user_id: int, limit: int = 12) -> list[dict[str, Any]]:
    user_key = f"site_user_{user_id}"
    matrix, user_map, movie_map, inv_users, inv_movies = _build_rating_matrix()
    if matrix.size == 0 or user_key not in user_map:
        return _fallback_popular(limit)

    uid = user_map[user_key]
    rated_movie_ids = {
        inv_movies[mid_idx]
        for mid_idx, score in enumerate(matrix[uid])
        if score > 0
    }

    try:
        n_components = min(20, matrix.shape[1] - 1, matrix.shape[0] - 1)
        if n_components < 2:
            return _content_based_for_user(user_id, limit)
        model = NMF(n_components=n_components, init="nndsvda", max_iter=300, random_state=42)
        user_features = model.fit_transform(matrix)
        item_features = model.components_.T
        predicted = user_features[uid] @ item_features.T

        ranked = []
        for mid_idx, score in enumerate(predicted):
            movie_id = inv_movies[mid_idx]
            if movie_id in rated_movie_ids:
                continue
            ranked.append((float(score), movie_id))
        ranked.sort(reverse=True)
        movie_ids = [mid for _, mid in ranked[: limit * 2]]
        movies = get_movies_by_ids(movie_ids)
        return movies[:limit]
    except Exception:
        return _content_based_for_user(user_id, limit)


def _content_based_for_user(user_id: int, limit: int) -> list[dict[str, Any]]:
    ratings = UserRating.query.filter_by(user_id=user_id).all()
    if not ratings:
        return _fallback_popular(limit)

    seed_ids = [r.movie_id for r in ratings[:3]]
    seen = set(seed_ids)
    results: list[dict[str, Any]] = []
    for mid in seed_ids:
        for movie in get_similar_movies(mid, limit=6):
            if movie["movie_id"] not in seen:
                seen.add(movie["movie_id"])
                results.append(movie)
            if len(results) >= limit:
                return results
    return results or _fallback_popular(limit)


def _fallback_popular(limit: int) -> list[dict[str, Any]]:
    data = list_movies(page=1, page_size=limit, sort="popular")
    return data["items"]


def recommend_graph_similar(movie_id: int, limit: int = 12) -> list[dict[str, Any]]:
    """GraphX/Neo4j 思路的图相似推荐：类型-导演-演员多关系融合。"""
    return get_similar_movies(movie_id, limit=limit)


def refresh_user_recommendations(user_id: int) -> list[dict[str, Any]]:
    RecommendationCache.query.filter_by(user_id=user_id).delete()
    movies = recommend_als_for_user(user_id, limit=15)
    for idx, movie in enumerate(movies):
        db.session.add(
            RecommendationCache(
                user_id=user_id,
                movie_id=movie["movie_id"],
                score=1.0 - idx * 0.03,
                algorithm="spark_als_local",
            )
        )
    db.session.commit()
    return movies


def get_cached_recommendations(user_id: int) -> list[dict[str, Any]]:
    rows = (
        RecommendationCache.query.filter_by(user_id=user_id)
        .order_by(RecommendationCache.score.desc())
        .limit(15)
        .all()
    )
    if not rows:
        movies = refresh_user_recommendations(user_id)
        return movies
    movie_ids = [row.movie_id for row in rows]
    return get_movies_by_ids(movie_ids)
