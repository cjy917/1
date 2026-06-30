"""
推荐算法服务模块

【核心算法】
NMF-ALS 在线协同过滤算法：
  输入：用户评分矩阵 R ∈ R^(n_users × n_movies)
  模型：R ≈ U × V^T，其中 U 为用户特征矩阵，V 为物品特征矩阵
  参数：n_components = min(20, n_movies-1, n_users-1)，max_iter=300，init="nndsvda"
  
【调用链】
recommendation_service.py → recommend_als_for_user() → movie_service.py.get_movies_by_ids()

【降级策略】
  1. NMF失败 → content_based_for_user（内容相似推荐）
  2. 内容推荐无数据 → fallback_popular（热门电影兜底）
"""

import csv
from collections import defaultdict
from typing import Any

import numpy as np
from sklearn.decomposition import NMF

from config import RATINGS_CSV
from models import CrawledRating, RecommendationCache, UserRating, db
from services.movie_service import get_movies_by_ids, get_similar_movies, list_movies


def seed_crawled_ratings(force: bool = False) -> int:
    """
    从CSV文件导入爬虫评分数据到 SQLite
    
    Args:
        force: 是否强制重新导入（清空原有数据）
    
    Returns:
        导入的评分记录数
    
    数据来源：
        - RATINGS_CSV（ratings.csv）：约33830条评分数据
        - 包含 user_id、movie_id、rating、source 字段
    """
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
    """
    构建用户-电影评分矩阵（稀疏矩阵）
    
    Returns:
        matrix: 评分矩阵 shape=(n_users, n_movies)
        user_map: 用户名 → 矩阵行索引映射
        movie_map: 电影ID → 矩阵列索引映射
        inv_users: 用户索引 → 用户名列表
        inv_movies: 电影索引 → 电影ID列表
    
    数据来源：
        1. CrawledRating（爬虫评分）：豆瓣/TMDb爬取的评分数据
        2. UserRating（用户评分）：系统用户的评分数据
    """
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
    """
    NMF-ALS 在线协同过滤推荐（核心算法）
    
    Args:
        user_id: 用户ID
        limit: 返回推荐数量
    
    Returns:
        推荐电影列表（含电影详情）
    
    算法流程：
        1. 构建评分矩阵（合并爬虫评分 + 用户评分）
        2. NMF分解：R ≈ U × V^T
        3. 预测用户对所有电影的评分
        4. 过滤已评分电影，按预测评分排序
        5. 获取电影详情返回
        
    降级策略：
        - NMF失败 → 内容相似推荐
        - 内容推荐无数据 → 热门电影兜底
    """
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
    """
    内容相似推荐（降级策略）
    
    Args:
        user_id: 用户ID
        limit: 返回推荐数量
    
    Returns:
        基于用户已评分电影的相似电影列表
    
    算法逻辑：
        1. 获取用户最近3部已评分电影
        2. 对每部电影获取6部相似电影（基于类型、导演、演员）
        3. 去重后返回
    """
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
    """
    热门电影兜底（最终降级策略）
    
    Args:
        limit: 返回推荐数量
    
    Returns:
        按热门度排序的电影列表
    """
    data = list_movies(page=1, page_size=limit, sort="popular")
    return data["items"]


def recommend_graph_similar(movie_id: int, limit: int = 12) -> list[dict[str, Any]]:
    """
    图相似推荐（GraphX思路）
    
    Args:
        movie_id: 电影ID
        limit: 返回推荐数量
    
    Returns:
        基于类型-导演-演员多关系融合的相似电影列表
    
    算法思路：
        基于电影的类型、导演、演员等属性计算相似度
        融合多维度关系，模拟图神经网络的推荐思路
    """
    return get_similar_movies(movie_id, limit=limit)


def refresh_user_recommendations(user_id: int) -> list[dict[str, Any]]:
    """
    刷新用户推荐缓存
    
    Args:
        user_id: 用户ID
    
    Returns:
        重新计算后的推荐电影列表
    
    逻辑：
        1. 删除用户旧的推荐缓存
        2. 调用 recommend_als_for_user 重新计算
        3. 将结果存入 RecommendationCache
    """
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
    """
    获取用户推荐缓存
    
    Args:
        user_id: 用户ID
    
    Returns:
        缓存的推荐电影列表（无缓存时自动刷新）
    
    逻辑：
        1. 查询 RecommendationCache
        2. 有缓存：直接返回
        3. 无缓存：调用 refresh_user_recommendations 刷新后返回
    """
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