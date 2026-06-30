"""Spark 批处理推荐：用户点「刷新」时在 VM 重算 ALS/GraphX/Content，展示读本地 JSON。"""
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
    """在线 ALS / 协同依赖爬虫评分矩阵，启动时若未导入则同步加载一次。"""
    if CrawledRating.query.count() == 0:
        seed_crawled_ratings()


def _short_title(title: str | None, max_len: int = 12) -> str:
    text = (title or "该电影").strip()
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _user_top_ratings(user_id: int, limit: int = 3) -> list[tuple[str, float, dict[str, Any] | None]]:
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
    tops = _user_top_ratings(user_id, limit=1)
    prefix = "在线 ALS" if online else "ALS"
    if tops:
        title, score, _ = tops[0]
        return f"因为你给《{_short_title(title)}》打了 {score:.1f} 分，{prefix} 猜你还想再看"
    return f"{prefix}：根据你当前的评分矩阵实时预测"


def _reason_for_graphx(*, online: bool = True) -> str:
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
    """与首页 /api/movies/home 的 popular 区块使用同一数据源。"""
    movies = get_home_sections().get("popular", [])[:limit]
    return [
        _movie_card(m, m.get("rating") or 0, "popular", _reason_for_cold_start(m))
        for m in movies
    ]


def get_cold_start_movies(limit: int = 12) -> list[dict[str, Any]]:
    return get_home_popular_items(limit)


def get_content_similar_movies(movie_id: int | str, limit: int = 10) -> list[dict[str, Any]]:
    similar = get_similar_movies(int(movie_id), limit=limit)
    return [_movie_card(m, (m.get("rating") or 0) / 10.0, "content") for m in similar]


def _load_spark_candidates(filename: str, user_key: int | str) -> list[dict[str, Any]]:
    path = SPARK_OUTPUT_DIR / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    uid = int(user_key)
    return [x for x in payload.get("items", []) if int(x.get("userId", -1)) == uid]


def _normalize_scores(items: list[dict], movie_id_key: str = "movieId") -> dict[str, float]:
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
    """在线 NMF-ALS：基于 SQLite 当前评分 + 爬虫评分矩阵实时分解。"""
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
    """图相似扩展：基于用户高分电影在类型/导演关系上的邻居。"""
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
    """在线协同过滤 + 图相似：用户重叠协同为主，图邻居扩展为辅。"""
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
    """评满 3 部后：全在线计算，不读 Spark 离线 JSON。"""
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
    genres: set[str] = set()
    for _, _, movie in _user_top_ratings(user_id, limit=5):
        if not movie:
            continue
        raw = (movie.get("genres") or "").replace(" ", "")
        genres.update(g for g in raw.split("/") if g)
    return genres


def _default_reason(algorithm: str, movie: dict[str, Any], user_id: int | None = None) -> str:
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
    path = SPARK_OUTPUT_DIR / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return [x for x in payload.get("items", []) if int(x.get("userId", -1)) == spark_user_id]


def _spark_has_outputs() -> bool:
    return all(
        (SPARK_OUTPUT_DIR / name).exists()
        for name in (
            "recommendations_als.json",
            "recommendations_graphx.json",
            "recommendations_content.json",
        )
    )


def _spark_score_map(filename: str, spark_user_id: int) -> dict[str, float]:
    return _normalize_scores(_load_user_spark_raw(filename, spark_user_id), movie_id_key="movieId")


def _reason_for_spark_als(user_id: int) -> str:
    tops = _user_top_ratings(user_id, limit=1)
    if tops:
        title, score, _ = tops[0]
        return f"Spark ALS：基于全量评分矩阵，参考你对《{_short_title(title)}》的 {score:.1f} 分"
    return "Spark ALS：Spark MLlib 协同过滤"


def _reason_for_spark_graphx() -> str:
    return "Spark GraphX：用户-电影图上的协同扩展推荐"


def _reason_for_spark_content() -> str:
    return "Spark TF-IDF：类型/导演/演员等内容向量相似"


def _reason_for_spark_hybrid(algos: list[str], user_id: int) -> str:
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
    """从本地 spark/output/*.json 读取该用户推荐（由 VM 批处理产出）。"""
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
    """导出评分 → 同步 VM → 触发 Spark 批处理 → 拉回 JSON → 返回推荐。"""
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

    # 评满 3 部：只展示上次 Spark 批处理结果；新评分需用户点「刷新推荐」才重算
    return _spark_hybrid_recommendations(user_id, rating_count)


def import_spark_results() -> dict[str, int]:
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
