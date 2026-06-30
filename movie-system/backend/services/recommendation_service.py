"""
推荐策略服务模块（推荐系统核心调度层）

【推荐策略总览】
┌─────────────────────────────────────────────────────────────┐
│  用户评分数量 < 3（冷启动）                                   │
│    └── 返回热门电影（get_home_popular_items）               │
├─────────────────────────────────────────────────────────────┤
│  用户评分数量 >= 3（正常推荐）                                │
│    ├── 优先读取 Spark 离线 JSON（_spark_hybrid_recommendations） │
│    ├── 无 Spark 输出 → 在线混合推荐（_online_hybrid_recommendations） │
│    └── 用户点击「刷新」→ 触发 Spark VM 批处理                 │
└─────────────────────────────────────────────────────────────┘

【混合推荐权重】
  WEIGHT_ALS = 0.7（协同过滤为主）
  WEIGHT_GRAPHX = 0.2（图相似扩展）
  WEIGHT_CONTENT = 0.1（内容相似兜底）

【调用链】
app.py → hybrid_recommendations() → _spark_hybrid_recommendations() / _online_hybrid_recommendations()
                                        ↓
                              recommend_service.py.recommend_als_for_user()
                              movie_service.py.get_movies_by_ids()
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from config import (
    RECOMMEND_TOP_N,
    SPARK_OUTPUT_DIR,
    SPARK_USER_OFFSET,
    WEIGHT_ALS,
    WEIGHT_CONTENT,
    WEIGHT_GRAPHX,
)
from models import CrawledRating, SparkRecommendation, UserRating, db
from services.movie_service import (
    get_home_sections,
    get_movie_by_id,
    get_movies_by_ids,
    get_similar_movies,
)
from services.recommend_service import recommend_als_for_user, seed_crawled_ratings

STRATEGY_LABELS = {
    "spark_hybrid": "Spark 混合推荐 (ALS 0.7 + GraphX 0.2 + TF-IDF 0.1)",
    "spark_pending": "待刷新 · 请点击「刷新推荐」在 VM 上运行 Spark",
    "online_hybrid": "在线混合推荐 (NMF-ALS 0.7 + 在线协同 0.2 + TF-IDF 0.1)",
    "hybrid": "在线混合推荐 (NMF-ALS 0.7 + 在线协同 0.2 + TF-IDF 0.1)",
    "cold_start_partial": "冷启动模式 (GraphX + 内容相似)",
    "cold_start": "冷启动 · 与首页「热门电影」相同",
    "imported": "Spark 离线推荐结果（管理员导入）",
}

SECTION_LIMIT = 20
RATING_MIN_FOR_PERSONAL = 3


def _ensure_crawled_ratings() -> None:
    """
    确保爬虫评分数据已加载
    
    在线 ALS/协同算法依赖爬虫评分矩阵，启动时若未导入则同步加载一次
    """
    if CrawledRating.query.count() == 0:
        seed_crawled_ratings()


def _short_title(title: str | None, max_len: int = 12) -> str:
    """电影标题截断（用于推荐理由展示）"""
    text = (title or "该电影").strip()
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _user_top_ratings(user_id: int, limit: int = 3) -> list[tuple[str, float, dict[str, Any] | None]]:
    """
    获取用户评分最高的电影
    
    Args:
        user_id: 用户ID
        limit: 返回数量
    
    Returns:
        [(电影标题, 评分, 电影详情dict), ...]
    """
    rows = (
        UserRating.query.filter_by(user_id=user_id)
        .order_by(UserRating.score.desc())
        .limit(limit)
        .all()
    )
    result: list[tuple[str, float, dict[str, Any] | None]] = []
    for row in rows:
        movie = get_movie_by_id(row.movie_id)
        title = movie.get("title") if movie else str(row.movie_id)
        result.append((title, float(row.score), movie))
    return result


def _reason_for_als(user_id: int, *, online: bool = True) -> str:
    """生成 ALS 推荐理由"""
    tops = _user_top_ratings(user_id, limit=1)
    prefix = "在线 ALS" if online else "ALS"
    if tops:
        title, score, _ = tops[0]
        return f"因为你给《{_short_title(title)}》打了 {score:.1f} 分，{prefix} 猜你还想再看"
    return f"{prefix}：根据你当前的评分矩阵实时预测"


def _reason_for_graphx(*, online: bool = True) -> str:
    """生成 GraphX/图相似推荐理由"""
    if online:
        return "在线协同：与你评分口味相近的用户也在看这些电影"
    return "GraphX：口味相似的用户也在看这些电影"


def _reason_for_content(
    movie: dict[str, Any],
    *,
    source_title: str | None = None,
    source_score: float | None = None,
    user_genres: set[str] | None = None,
) -> str:
    """生成内容相似推荐理由"""
    if source_title and source_score:
        return f"与你给《{_short_title(source_title)}》打的 {source_score:.1f} 分相关，内容/类型相近"
    genres = (movie.get("genres") or "").replace(" ", "")
    movie_genres = {g for g in genres.split("/") if g}
    if user_genres and movie_genres & user_genres:
        hit = next(iter(movie_genres & user_genres))
        return f"与你常看的「{hit}」类电影相似"
    if movie_genres:
        return f"TF-IDF 内容相似：接近你喜欢的「{next(iter(movie_genres))}」类型"
    return "内容相似：基于电影简介与类型的 TF-IDF 匹配"


def _reason_for_hybrid(algos: list[str], movie: dict[str, Any], user_id: int) -> str:
    """生成混合推荐理由"""
    parts: list[str] = []
    if "als" in algos:
        tops = _user_top_ratings(user_id, limit=1)
        if tops:
            title, score, _ = tops[0]
            parts.append(f"参考你对《{_short_title(title)}》的 {score:.1f} 分")
        else:
            parts.append("你的评分偏好")
    if "graphx" in algos:
        parts.append("相似用户也在看")
    if "content" in algos:
        genres = (movie.get("genres") or "").replace(" ", "")
        g = [x for x in genres.split("/") if x]
        if g:
            parts.append(f"「{g[0]}」类型匹配")
        else:
            parts.append("内容类型相近")
    if parts:
        return "混合推荐：" + " · ".join(parts)
    return "混合推荐：多算法融合排序"


def _reason_for_cold_start(movie: dict[str, Any]) -> str:
    """生成冷启动推荐理由"""
    rating = movie.get("rating")
    if rating:
        return f"首页热门电影 · 豆瓣 {float(rating):.1f} 分 · 评价人数多"
    return "与首页「热门电影」栏目一致"


def _movie_card(
    movie: dict[str, Any],
    score: float,
    algorithm: str,
    reason: str | None = None,
) -> dict[str, Any]:
    """
    组装推荐电影卡片（统一格式）
    
    Args:
        movie: 电影详情
        score: 推荐得分
        algorithm: 算法类型（als/graphx/content/hybrid）
        reason: 推荐理由
    
    Returns:
        推荐卡片 dict（含 movie_id, title, poster_url, score, algorithm, genres, rating, reason）
    """
    card = {
        "movie_id": movie["movie_id"],
        "title": movie.get("title"),
        "poster_url": movie.get("poster_url") or f"/api/posters/{movie['movie_id']}",
        "score": round(float(score), 1),
        "algorithm": algorithm,
        "genres": movie.get("genres"),
        "rating": round(float(movie["rating"]), 1) if movie.get("rating") not in (None, "") else movie.get("rating"),
    }
    if reason:
        card["reason"] = reason
    return card


def get_home_popular_items(limit: int = SECTION_LIMIT) -> list[dict[str, Any]]:
    """获取首页热门电影（冷启动兜底）"""
    movies = get_home_sections().get("popular", [])[:limit]
    return [
        _movie_card(m, m.get("rating") or 0, "popular", _reason_for_cold_start(m))
        for m in movies
    ]


def get_cold_start_movies(limit: int = 12) -> list[dict[str, Any]]:
    """获取冷启动推荐电影（调用热门电影接口）"""
    return get_home_popular_items(limit)


def get_content_similar_movies(movie_id: int | str, limit: int = 10) -> list[dict[str, Any]]:
    """获取内容相似电影列表"""
    similar = get_similar_movies(int(movie_id), limit=limit)
    return [_movie_card(m, (m.get("rating") or 0) / 10.0, "content") for m in similar]


def _load_spark_candidates(filename: str, user_key: int | str) -> list[dict[str, Any]]:
    """从 Spark 输出 JSON 文件加载推荐候选"""
    path = SPARK_OUTPUT_DIR / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    uid = int(user_key)
    return [x for x in payload.get("items", []) if int(x.get("userId", -1)) == uid]


def _normalize_scores(items: list[dict], movie_id_key: str = "movieId") -> dict[str, float]:
    """将推荐得分归一化到 [0, 1] 区间"""
    if not items:
        return {}
    scores = [float(x.get("score", 0)) for x in items]
    min_s, max_s = min(scores), max(scores)
    span = max_s - min_s if max_s > min_s else 1.0
    return {str(item[movie_id_key]): (float(item.get("score", 0)) - min_s) / span for item in items}


def _content_recommendations_for_user(
    user_id: int,
    limit: int = 10,
    rated_movie_ids: set[str] | None = None,
) -> tuple[dict[str, float], dict[str, str]]:
    """
    内容相似推荐（TF-IDF）
    
    Args:
        user_id: 用户ID
        limit: 返回数量
        rated_movie_ids: 用户已评分电影ID集合
    
    Returns:
        (推荐得分dict, 推荐理由dict)
    
    算法逻辑：
        1. 获取用户评分最高的前10部电影
        2. 对每部电影获取相似电影（基于类型、导演、演员）
        3. 根据用户评分加权（评分越高权重越大）
        4. 去重并归一化得分
    """
    all_ratings = (
        UserRating.query.filter_by(user_id=user_id)
        .order_by(UserRating.score.desc())
        .all()
    )
    if not all_ratings:
        return {}, {}

    rated_ids = rated_movie_ids or {str(r.movie_id) for r in all_ratings}
    seeds = all_ratings[:10]
    aggregated: dict[str, float] = {}
    reasons: dict[str, str] = {}

    for rating in seeds:
        source = get_movie_by_id(rating.movie_id)
        source_title = source.get("title") if source else str(rating.movie_id)
        similar = get_similar_movies(rating.movie_id, limit=limit)
        weight = max(rating.score, 1.0) / 10.0
        for idx, movie in enumerate(similar):
            mid = str(movie["movie_id"])
            if mid in rated_ids:
                continue
            item_score = (1.0 - idx * 0.05) * weight
            aggregated[mid] = aggregated.get(mid, 0.0) + item_score
            if mid not in reasons:
                reasons[mid] = _reason_for_content(
                    movie,
                    source_title=source_title,
                    source_score=float(rating.score),
                )

    if not aggregated:
        return {}, {}
    max_v = max(aggregated.values())
    return {k: v / max_v for k, v in aggregated.items()}, reasons


def _online_als_scores(user_id: int, limit: int, rated_movie_ids: set[str]) -> dict[str, float]:
    """
    在线 NMF-ALS 推荐得分
    
    Args:
        user_id: 用户ID
        limit: 返回数量
        rated_movie_ids: 用户已评分电影ID集合
    
    Returns:
        推荐得分 dict（movie_id → 得分）
    
    调用链：
        _online_als_scores → recommend_service.py.recommend_als_for_user()
    """
    movies = recommend_als_for_user(user_id, limit=limit + len(rated_movie_ids))
    if not movies:
        return {}
    scores: dict[str, float] = {}
    for idx, movie in enumerate(movies):
        mid = str(movie["movie_id"])
        if mid in rated_movie_ids:
            continue
        scores[mid] = max(0.05, 1.0 - idx * (0.9 / max(limit, 1)))
        if len(scores) >= limit:
            break
    return scores


def _graph_similar_scores(
    user_id: int, limit: int, rated_movie_ids: set[str]
) -> tuple[dict[str, float], dict[str, str]]:
    """
    图相似扩展得分（基于类型/导演关系的邻居推荐）
    
    Args:
        user_id: 用户ID
        limit: 返回数量
        rated_movie_ids: 用户已评分电影ID集合
    
    Returns:
        (推荐得分dict, 推荐理由dict)
    
    算法逻辑：
        1. 获取用户评分最高的前5部电影
        2. 对每部电影获取相似电影（基于类型、导演、演员）
        3. 根据用户评分加权，按位置衰减
        4. 去重并归一化得分
    """
    user_ratings = (
        UserRating.query.filter_by(user_id=user_id)
        .order_by(UserRating.score.desc())
        .limit(5)
        .all()
    )
    if not user_ratings:
        return {}, {}

    aggregated: dict[str, float] = {}
    reasons: dict[str, str] = {}
    for rating in user_ratings:
        for idx, movie in enumerate(get_similar_movies(rating.movie_id, limit=10)):
            mid = str(movie["movie_id"])
            if mid in rated_movie_ids:
                continue
            aggregated[mid] = aggregated.get(mid, 0.0) + (rating.score / 10.0) * (1.0 - idx * 0.07)
            if mid not in reasons:
                src = get_movie_by_id(rating.movie_id)
                title = src.get("title") if src else str(rating.movie_id)
                reasons[mid] = f"在线图相似：与《{_short_title(title)}》类型/关系相近"

    if not aggregated:
        return {}, {}
    max_v = max(aggregated.values())
    ranked = dict(sorted(aggregated.items(), key=lambda x: -x[1])[: limit + len(rated_movie_ids)])
    return {k: v / max_v for k, v in ranked.items()}, reasons


def _merge_score_maps(*maps: dict[str, float]) -> dict[str, float]:
    """合并多个推荐得分字典（加权求和后归一化）"""
    merged: dict[str, float] = {}
    for score_map in maps:
        for mid, score in score_map.items():
            merged[mid] = merged.get(mid, 0.0) + score
    if not merged:
        return {}
    max_v = max(merged.values())
    return {k: v / max_v for k, v in merged.items()}


def _online_graphx_scores(
    user_id: int, limit: int, rated_movie_ids: set[str]
) -> tuple[dict[str, float], dict[str, str]]:
    """
    在线协同过滤 + 图相似得分
    
    Args:
        user_id: 用户ID
        limit: 返回数量
        rated_movie_ids: 用户已评分电影ID集合
    
    Returns:
        (推荐得分dict, 推荐理由dict)
    
    算法逻辑：
        1. 用户重叠协同：找到与用户评分重叠的爬虫用户，推荐他们评分高的电影
        2. 图相似扩展：基于用户高分电影的类型/导演邻居
        3. 合并两种得分并归一化
    """
    user_ratings = UserRating.query.filter_by(user_id=user_id).all()
    if not user_ratings:
        return {}, {}

    seed = {r.movie_id: float(r.score) for r in user_ratings}
    seed_ids = set(seed.keys())
    reasons: dict[str, str] = {}

    crawled_seed = CrawledRating.query.filter(CrawledRating.movie_id.in_(seed_ids)).all()
    neighbor_overlap: dict[str, set[int]] = {}
    for row in crawled_seed:
        neighbor_overlap.setdefault(row.user_name, set()).add(row.movie_id)

    candidate_scores: dict[int, float] = {}
    if neighbor_overlap:
        neighbor_names = list(neighbor_overlap.keys())
        neighbor_rows = CrawledRating.query.filter(CrawledRating.user_name.in_(neighbor_names)).all()
        rows_by_user: dict[str, list[CrawledRating]] = defaultdict(list)
        for row in neighbor_rows:
            rows_by_user[row.user_name].append(row)

        for user_name, overlap_mids in neighbor_overlap.items():
            if not overlap_mids:
                continue
            overlap_score = sum(seed[mid] for mid in overlap_mids if mid in seed) / len(overlap_mids)
            if overlap_score < 2.0:
                continue
            for row in rows_by_user.get(user_name, []):
                if row.movie_id in seed_ids:
                    continue
                candidate_scores[row.movie_id] = (
                    candidate_scores.get(row.movie_id, 0.0) + overlap_score * row.score
                )

    collab_norm: dict[str, float] = {}
    if candidate_scores:
        max_v = max(candidate_scores.values())
        collab_norm = {
            str(mid): score / max_v
            for mid, score in sorted(candidate_scores.items(), key=lambda x: -x[1])[
                : limit + len(rated_movie_ids)
            ]
            if str(mid) not in rated_movie_ids
        }
        for mid in list(collab_norm.keys())[:limit]:
            if mid not in reasons:
                reasons[mid] = _reason_for_graphx()

    graph_norm, graph_reasons = _graph_similar_scores(user_id, limit, rated_movie_ids)
    reasons.update(graph_reasons)
    merged = _merge_score_maps(collab_norm, graph_norm)
    return merged, reasons


def _online_hybrid_recommendations(user_id: int, rating_count: int) -> dict[str, Any]:
    """
    在线混合推荐（无 Spark 输出时的降级方案）
    
    Args:
        user_id: 用户ID
        rating_count: 用户评分数量
    
    Returns:
        混合推荐结果（含混合推荐 + 各算法独立结果）
    
    算法流程：
        1. 并行计算三种算法得分：
           - _online_als_scores（NMF-ALS，权重0.7）
           - _online_graphx_scores（图相似，权重0.2）
           - _content_recommendations_for_user（内容相似，权重0.1）
        2. 加权融合生成混合推荐
        3. 同时返回各算法独立结果用于对比展示
    """
    rated_movie_ids = {str(r.movie_id) for r in UserRating.query.filter_by(user_id=user_id).all()}
    pool = SECTION_LIMIT + 10

    als_norm = _online_als_scores(user_id, pool, rated_movie_ids)
    graphx_norm, graphx_reasons = _online_graphx_scores(user_id, pool, rated_movie_ids)
    content_scores, content_reasons = _content_recommendations_for_user(
        user_id, limit=pool, rated_movie_ids=rated_movie_ids
    )

    fused: dict[str, dict[str, Any]] = {}

    def _add(mid: str, score: float, algo: str) -> None:
        if mid in rated_movie_ids:
            return
        if mid not in fused:
            fused[mid] = {"score": 0.0, "algos": []}
        fused[mid]["score"] += score
        fused[mid]["algos"].append(algo)

    for mid, s in als_norm.items():
        _add(mid, s * WEIGHT_ALS, "als")
    for mid, s in graphx_norm.items():
        _add(mid, s * WEIGHT_GRAPHX, "graphx")
    for mid, s in content_scores.items():
        _add(mid, s * WEIGHT_CONTENT, "content")

    hybrid_items: list[dict[str, Any]] = []
    if fused:
        ranked = sorted(fused.items(), key=lambda x: -x[1]["score"])[:SECTION_LIMIT]
        movie_map = {str(m["movie_id"]): m for m in get_movies_by_ids([int(mid) for mid, _ in ranked])}
        for mid, meta in ranked:
            movie = movie_map.get(mid) or get_movie_by_id(int(mid))
            if not movie:
                continue
            algo = "+".join(sorted(set(meta["algos"])))
            reason = _reason_for_hybrid(sorted(set(meta["algos"])), movie, user_id)
            hybrid_items.append(_movie_card(movie, meta["score"], algo, reason))

    als_items = _rank_to_items(als_norm, "als", rated_movie_ids, SECTION_LIMIT, user_id=user_id)
    graphx_items = _rank_to_items(
        graphx_norm,
        "graphx",
        rated_movie_ids,
        SECTION_LIMIT,
        reasons_map=graphx_reasons,
        user_id=user_id,
    )
    content_items = _rank_to_items(
        content_scores,
        "content",
        rated_movie_ids,
        SECTION_LIMIT,
        reasons_map=content_reasons,
        user_id=user_id,
    )

    popular_items = get_home_popular_items(limit=SECTION_LIMIT)
    if not hybrid_items and not als_items and not graphx_items and not content_items:
        return _build_sections_payload(
            hybrid_items=[],
            als_items=[],
            graphx_items=[],
            content_items=[],
            popular_items=popular_items,
            strategy="online_hybrid",
            source="online",
            rating_count=rating_count,
            spark_imported=False,
            personalized_ready=True,
        )

    return _build_sections_payload(
        hybrid_items=hybrid_items[:SECTION_LIMIT],
        als_items=als_items,
        graphx_items=graphx_items,
        content_items=content_items,
        popular_items=[],
        strategy="online_hybrid",
        source="online",
        rating_count=rating_count,
        spark_imported=False,
        personalized_ready=True,
    )


def _user_preferred_genres(user_id: int) -> set[str]:
    """获取用户偏好的电影类型（基于高分电影）"""
    genres: set[str] = set()
    for _, _, movie in _user_top_ratings(user_id, limit=5):
        if not movie:
            continue
        raw = (movie.get("genres") or "").replace(" ", "")
        genres.update(g for g in raw.split("/") if g)
    return genres


def _default_reason(algorithm: str, movie: dict[str, Any], user_id: int | None = None) -> str:
    """根据算法类型生成默认推荐理由"""
    if algorithm == "als":
        return _reason_for_als(user_id) if user_id else "在线 ALS 协同过滤"
    if algorithm == "graphx":
        return _reason_for_graphx()
    if algorithm == "content":
        return _reason_for_content(movie, user_genres=_user_preferred_genres(user_id) if user_id else None)
    if algorithm == "cold_start":
        return _reason_for_cold_start(movie)
    if "+" in algorithm and user_id:
        return _reason_for_hybrid(algorithm.split("+"), movie, user_id)
    return "个性化推荐"


def _rank_to_items(
    score_map: dict[str, float],
    algorithm: str,
    rated_movie_ids: set[str],
    limit: int,
    *,
    reasons_map: dict[str, str] | None = None,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    """
    将得分字典转换为推荐电影卡片列表
    
    Args:
        score_map: 推荐得分字典
        algorithm: 算法类型
        rated_movie_ids: 用户已评分电影ID集合
        limit: 返回数量
        reasons_map: 推荐理由字典
        user_id: 用户ID
    
    Returns:
        推荐电影卡片列表
    """
    if not score_map:
        return []
    ranked = sorted(score_map.items(), key=lambda x: -x[1])
    candidate_ids = [int(mid) for mid, _ in ranked[: limit + len(rated_movie_ids)]]
    movie_map = {str(m["movie_id"]): m for m in get_movies_by_ids(candidate_ids)}
    items: list[dict[str, Any]] = []
    for mid, score in ranked:
        if mid in rated_movie_ids:
            continue
        movie = movie_map.get(mid) or get_movie_by_id(int(mid))
        if not movie:
            continue
        reason = (reasons_map or {}).get(mid) or _default_reason(algorithm, movie, user_id)
        items.append(_movie_card(movie, score, algorithm, reason))
        if len(items) >= limit:
            break
    return items


def _items_from_db(
    user_id: int,
    limit: int,
    algorithm: str | None = None,
) -> list[dict[str, Any]] | None:
    """从数据库读取 Spark 离线推荐结果"""
    query = SparkRecommendation.query.filter_by(user_id=user_id)
    if algorithm:
        query = query.filter_by(algorithm=algorithm)
    rows = query.order_by(SparkRecommendation.score.desc()).limit(limit).all()
    if not rows:
        return None
    movie_ids = [int(r.movie_id) for r in rows]
    movies = {m["movie_id"]: m for m in get_movies_by_ids(movie_ids)}
    items = []
    for row in rows:
        movie = movies.get(row.movie_id) or movies.get(int(row.movie_id))
        if not movie:
            continue
        algo = row.algorithm or algorithm or "hybrid"
        reason = _default_reason(algo, movie, user_id)
        items.append(_movie_card(movie, row.score, algo, reason))
    return items or None


def _build_sections_payload(
    *,
    hybrid_items: list[dict[str, Any]],
    als_items: list[dict[str, Any]],
    graphx_items: list[dict[str, Any]],
    content_items: list[dict[str, Any]],
    popular_items: list[dict[str, Any]],
    strategy: str,
    source: str,
    rating_count: int,
    spark_imported: bool,
    personalized_ready: bool = False,
) -> dict[str, Any]:
    """
    构建推荐结果 payload（统一返回格式）
    
    Args:
        hybrid_items: 混合推荐结果
        als_items: ALS独立推荐结果
        graphx_items: GraphX独立推荐结果
        content_items: 内容相似独立推荐结果
        popular_items: 热门电影（冷启动用）
        strategy: 推荐策略类型
        source: 数据来源（online/spark/fallback）
        rating_count: 用户评分数量
        spark_imported: 是否已导入Spark结果
        personalized_ready: 是否可以展示个性化推荐
    
    Returns:
        推荐结果字典（含所有推荐列表和元信息）
    """
    primary_items = hybrid_items if hybrid_items else (popular_items if strategy != "spark_pending" else [])
    return {
        "items": primary_items,
        "hybrid_items": hybrid_items,
        "als_items": als_items,
        "graphx_items": graphx_items,
        "content_items": content_items,
        "popular_items": popular_items,
        "source": source,
        "strategy": strategy,
        "strategy_label": STRATEGY_LABELS.get(strategy, STRATEGY_LABELS["hybrid"]),
        "rating_count": rating_count,
        "spark_imported": spark_imported,
        "personalized_ready": personalized_ready,
        "rating_required": RATING_MIN_FOR_PERSONAL,
    }


def _load_user_spark_raw(filename: str, spark_user_id: int) -> list[dict]:
    """从 Spark 输出 JSON 文件加载指定用户的推荐数据"""
    path = SPARK_OUTPUT_DIR / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return [x for x in payload.get("items", []) if int(x.get("userId", -1)) == spark_user_id]


def _spark_has_outputs() -> bool:
    """检查 Spark 批处理输出文件是否存在"""
    return all(
        (SPARK_OUTPUT_DIR / name).exists()
        for name in (
            "recommendations_als.json",
            "recommendations_graphx.json",
            "recommendations_content.json",
        )
    )


def _spark_score_map(filename: str, spark_user_id: int) -> dict[str, float]:
    """加载 Spark 输出并归一化得分"""
    return _normalize_scores(_load_user_spark_raw(filename, spark_user_id), movie_id_key="movieId")


def _reason_for_spark_als(user_id: int) -> str:
    """生成 Spark ALS 推荐理由"""
    tops = _user_top_ratings(user_id, limit=1)
    if tops:
        title, score, _ = tops[0]
        return f"Spark ALS：基于全量评分矩阵，参考你对《{_short_title(title)}》的 {score:.1f} 分"
    return "Spark ALS：Spark MLlib 协同过滤"


def _reason_for_spark_graphx() -> str:
    """生成 Spark GraphX 推荐理由"""
    return "Spark GraphX：用户-电影图上的协同扩展推荐"


def _reason_for_spark_content() -> str:
    """生成 Spark TF-IDF 内容推荐理由"""
    return "Spark TF-IDF：类型/导演/演员等内容向量相似"


def _reason_for_spark_hybrid(algos: list[str], user_id: int) -> str:
    """生成 Spark 混合推荐理由"""
    parts: list[str] = []
    if "als" in algos:
        tops = _user_top_ratings(user_id, limit=1)
        if tops:
            title, score, _ = tops[0]
            parts.append(f"Spark ALS 参考《{_short_title(title)}》{score:.1f} 分")
        else:
            parts.append("Spark ALS")
    if "graphx" in algos:
        parts.append("GraphX 图协同")
    if "content" in algos:
        parts.append("TF-IDF 内容相似")
    return "Spark 混合：" + " · ".join(parts) if parts else "Spark 混合推荐"


def _spark_hybrid_recommendations(
    user_id: int,
    rating_count: int,
    *,
    refreshed: bool = False,
) -> dict[str, Any]:
    """
    Spark 离线混合推荐（优先推荐策略）
    
    Args:
        user_id: 用户ID
        rating_count: 用户评分数量
        refreshed: 是否刚刷新过
    
    Returns:
        混合推荐结果
    
    算法流程：
        1. 检查 Spark 输出文件是否存在
        2. 加载三种算法的归一化得分：
           - recommendations_als.json（权重0.7）
           - recommendations_graphx.json（权重0.2）
           - recommendations_content.json（权重0.1）
        3. 加权融合生成混合推荐
        4. 同时返回各算法独立结果用于对比展示
    
    数据来源：
        Spark VM 批处理产出的 JSON 文件（spark/output/ 目录）
    """
    spark_uid = user_id + SPARK_USER_OFFSET
    rated_movie_ids = {str(r.movie_id) for r in UserRating.query.filter_by(user_id=user_id).all()}

    if not _spark_has_outputs():
        return _build_sections_payload(
            hybrid_items=[],
            als_items=[],
            graphx_items=[],
            content_items=[],
            popular_items=get_home_popular_items(limit=SECTION_LIMIT),
            strategy="spark_pending",
            source="spark",
            rating_count=rating_count,
            spark_imported=False,
            personalized_ready=False,
        )

    als_norm = _spark_score_map("recommendations_als.json", spark_uid)
    graphx_norm = _spark_score_map("recommendations_graphx.json", spark_uid)
    content_norm = _spark_score_map("recommendations_content.json", spark_uid)

    if not als_norm and not graphx_norm and not content_norm:
        return _build_sections_payload(
            hybrid_items=[],
            als_items=[],
            graphx_items=[],
            content_items=[],
            popular_items=get_home_popular_items(limit=SECTION_LIMIT),
            strategy="spark_pending",
            source="spark",
            rating_count=rating_count,
            spark_imported=True,
            personalized_ready=False,
        )

    fused: dict[str, dict[str, Any]] = {}

    def _add(mid: str, score: float, algo: str) -> None:
        if mid in rated_movie_ids:
            return
        if mid not in fused:
            fused[mid] = {"score": 0.0, "algos": []}
        fused[mid]["score"] += score
        fused[mid]["algos"].append(algo)

    for mid, s in als_norm.items():
        _add(mid, s * WEIGHT_ALS, "als")
    for mid, s in graphx_norm.items():
        _add(mid, s * WEIGHT_GRAPHX, "graphx")
    for mid, s in content_norm.items():
        _add(mid, s * WEIGHT_CONTENT, "content")

    hybrid_items: list[dict[str, Any]] = []
    if fused:
        ranked = sorted(fused.items(), key=lambda x: -x[1]["score"])[:SECTION_LIMIT]
        movie_map = {str(m["movie_id"]): m for m in get_movies_by_ids([int(mid) for mid, _ in ranked])}
        for mid, meta in ranked:
            movie = movie_map.get(mid) or get_movie_by_id(int(mid))
            if not movie:
                continue
            algos = sorted(set(meta["algos"]))
            algo = "+".join(algos)
            reason = _reason_for_spark_hybrid(algos, user_id)
            hybrid_items.append(_movie_card(movie, meta["score"], algo, reason))

    als_reasons = {mid: _reason_for_spark_als(user_id) for mid in als_norm}
    graphx_reasons = {mid: _reason_for_spark_graphx() for mid in graphx_norm}
    content_reasons = {mid: _reason_for_spark_content() for mid in content_norm}

    als_items = _rank_to_items(
        als_norm, "als", rated_movie_ids, SECTION_LIMIT, reasons_map=als_reasons, user_id=user_id
    )
    graphx_items = _rank_to_items(
        graphx_norm, "graphx", rated_movie_ids, SECTION_LIMIT, reasons_map=graphx_reasons, user_id=user_id
    )
    content_items = _rank_to_items(
        content_norm, "content", rated_movie_ids, SECTION_LIMIT, reasons_map=content_reasons, user_id=user_id
    )

    return _build_sections_payload(
        hybrid_items=hybrid_items[:SECTION_LIMIT],
        als_items=als_items,
        graphx_items=graphx_items,
        content_items=content_items,
        popular_items=[],
        strategy="spark_hybrid",
        source="spark",
        rating_count=rating_count,
        spark_imported=True,
        personalized_ready=refreshed or bool(hybrid_items),
    )


def refresh_spark_recommendations(user_id: int) -> dict[str, Any]:
    """
    刷新 Spark 推荐（用户点击「刷新推荐」时调用）
    
    Args:
        user_id: 用户ID
    
    Returns:
        刷新后的推荐结果
    
    执行流程：
        1. 导出评分数据（export_spark_ratings.py）
        2. 调用 Spark VM 批处理（spark_vm_client.py）
        3. 加载新的 Spark 输出 JSON
        4. 返回推荐结果
    """
    rating_count = UserRating.query.filter_by(user_id=user_id).count()
    if rating_count < RATING_MIN_FOR_PERSONAL:
        return hybrid_recommendations(user_id)

    import sys
    from pathlib import Path

    scripts_dir = Path(__file__).resolve().parent.parent.parent / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from export_spark_ratings import export_ratings

    export_ratings()

    from services.spark_vm_client import run_spark_pipeline_on_vm

    run_spark_pipeline_on_vm()
    return _spark_hybrid_recommendations(user_id, rating_count, refreshed=True)


def hybrid_recommendations(user_id: int, limit: int = RECOMMEND_TOP_N) -> dict[str, Any]:
    """
    推荐系统入口函数
    
    Args:
        user_id: 用户ID
        limit: 返回数量
    
    Returns:
        推荐结果（含策略信息、推荐列表）
    
    策略路由：
        1. 确保爬虫评分已加载
        2. 获取用户评分数量
        3. rating_count < 3 → 冷启动模式（返回热门电影）
        4. rating_count >= 3 → Spark 离线混合推荐
           - 有 Spark 输出 → 读取 JSON 展示
           - 无 Spark 输出 → 降级为在线混合推荐
    """
    _ensure_crawled_ratings()
    rating_count = UserRating.query.filter_by(user_id=user_id).count()
    popular_items = get_home_popular_items(limit=SECTION_LIMIT)

    if rating_count < RATING_MIN_FOR_PERSONAL:
        return _build_sections_payload(
            hybrid_items=[],
            als_items=[],
            graphx_items=[],
            content_items=[],
            popular_items=popular_items,
            strategy="cold_start",
            source="fallback",
            rating_count=rating_count,
            spark_imported=False,
            personalized_ready=False,
        )

    return _spark_hybrid_recommendations(user_id, rating_count)


def import_spark_results() -> dict[str, int]:
    """
    导入 Spark 推荐结果到数据库（管理员操作）
    
    Returns:
        各算法导入数量统计
    
    逻辑：
        1. 遍历 Spark 输出 JSON 文件
        2. 将推荐结果写入 SparkRecommendation 表
        3. 支持算法类型：als、graphx、content
    """
    from models import User

    files = [
        ("recommendations_als.json", "als"),
        ("recommendations.json", "als"),
        ("recommendations_graphx.json", "graphx"),
        ("recommendations_content.json", "content"),
    ]
    counts: dict[str, int] = {}
    web_offset = SPARK_USER_OFFSET

    for filename, algorithm in files:
        path = SPARK_OUTPUT_DIR / filename
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        algo = payload.get("algorithm", algorithm)
        for entry in payload.get("items", []):
            spark_uid = int(entry["userId"])
            if spark_uid < web_offset:
                continue
            user = User.query.get(spark_uid - web_offset)
            if not user:
                continue
            movie_id = int(entry["movieId"])
            if not get_movie_by_id(movie_id):
                continue
            SparkRecommendation.query.filter_by(
                user_id=user.id, movie_id=movie_id, algorithm=algo
            ).delete()
            db.session.add(
                SparkRecommendation(
                    user_id=user.id,
                    movie_id=movie_id,
                    score=float(entry["score"]),
                    algorithm=algo,
                )
            )
            counts[algo] = counts.get(algo, 0) + 1
        db.session.commit()

    return counts