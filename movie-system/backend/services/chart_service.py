"""影人板块数据服务（导演/演员榜单、详情、相关影人）。"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from services.movie_service import _row_to_movie, get_mysql, split_pipe

# 影人详情中样本电影最多 4 部  
FILMMAKER_SAMPLE_SIZE = 4
# 详情页「相关导演/演员」最多推荐 12 人
RELATED_FILMMAKER_LIMIT = 12
# 按影人查电影时的默认条数上限（详情页传 limit=None 表示不限制）
FILMMAKER_MOVIES_DEFAULT_LIMIT = 20


def get_filmmaker_overview(director_limit: int = 24, actor_limit: int = 24) -> dict[str, Any]:
    """
    影人列表页数据：统计库内导演/演员总数，并返回作品数 Top N 榜单。
    前端 ChartsView 打开时调用 GET /api/charts/filmmakers。
    """
    director_counter: Counter[str] = Counter()
    actor_counter: Counter[str] = Counter()
    with get_mysql() as conn:     #获取数据库连接
        with conn.cursor() as cursor:
            # 遍历 movies.directors 字段（多人用 | 分隔），统计每位导演作品数
            cursor.execute("SELECT directors FROM movies WHERE directors IS NOT NULL AND directors != ''")
            for row in cursor.fetchall():
                for name in split_pipe(row["directors"]):
                    director_counter[name] += 1
            # 同理统计 actors 字段
            cursor.execute("SELECT actors FROM movies WHERE actors IS NOT NULL AND actors != ''")
            for row in cursor.fetchall():
                for name in split_pipe(row["actors"]):
                    actor_counter[name] += 1

    return {
        "director_total": len(director_counter),   # 库内导演总人数（如 5340）
        "actor_total": len(actor_counter),
        "director_limit": director_limit,
        "actor_limit": actor_limit,
        "directors": _aggregate_filmmakers_from_counter(director_counter, "director", director_limit),
        "actors": _aggregate_filmmakers_from_counter(actor_counter, "actor", actor_limit),
    }


def _aggregate_filmmakers_from_counter(
    counter: Counter[str],
    role: str,
    top_n: int,
) -> list[dict[str, Any]]:
    """按作品数量降序取 Top N，并为每人附带 sample_movies（卡片四宫格海报用）。"""
    results: list[dict[str, Any]] = []
    for name, count in counter.most_common(top_n):
        sample = get_movies_by_filmmaker(name, role, limit=FILMMAKER_SAMPLE_SIZE)
        results.append(
            {
                "name": name,
                "movie_count": count,
                "sample_movies": sample,
                "poster_url": sample[0]["poster_url"] if sample else None,
            }
        )
    return results


def get_movies_by_filmmaker(
    name: str,
    role: str,
    *,
    limit: int | None = FILMMAKER_MOVIES_DEFAULT_LIMIT,
    only_rated: bool = True,
) -> list[dict[str, Any]]:
    """
    查询某位导演/演员参与的电影。
    role=director 查 directors 列，role=actor 查 actors 列，按评分排序。
    """
    column = "directors" if role == "director" else "actors"
    rating_clause = " AND rating > 0" if only_rated else ""
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            sql = f"""
                SELECT * FROM movies
                WHERE {column} LIKE %s{rating_clause}
                ORDER BY rating DESC, rating_count DESC, release_year DESC
            """
            params: list[Any] = [f"%{name}%"]
            if limit is not None:
                sql += " LIMIT %s"
                params.append(limit)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
    return [_row_to_movie(row) for row in rows]


def _peer_library_count(name: str, role: str) -> int:
    """某影人在库内的作品总数（相关影人卡片展示用）。"""
    column = "directors" if role == "director" else "actors"
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) AS total FROM movies WHERE {column} LIKE %s",
                (f"%{name}%",),
            )
            return int(cursor.fetchone()["total"] or 0)


def _dedupe_links(links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """相关影人关联条目去重。"""
    seen: set[tuple[Any, ...]] = set()
    unique: list[dict[str, Any]] = []
    for link in links:
        if link["type"] == "co_direct":
            key = ("co_direct", link.get("movie_id"), link.get("movie_title"))
        elif link["type"] == "co_star":
            key = ("co_star", link.get("movie_id"), link.get("movie_title"))
        else:
            key = (
                "shared_actor",
                link.get("via_actor"),
                link.get("subject_movie_title"),
                link.get("peer_movie_title"),
            )
        if key in seen:
            continue
        seen.add(key)
        unique.append(link)
    return unique


def _build_relation_summary(links: list[dict[str, Any]]) -> str:
    """生成相关影人卡片顶部摘要，如「共同执导 2 部电影 · 通过 3 位共用演员产生关联」。"""
    co_direct = sum(1 for link in links if link["type"] == "co_direct")
    shared_actor_links = [link for link in links if link["type"] == "shared_actor"]
    co_star = sum(1 for link in links if link["type"] == "co_star")
    parts: list[str] = []
    if co_direct:
        parts.append(f"共同执导 {co_direct} 部电影")
    if shared_actor_links:
        actor_count = len({link["via_actor"] for link in shared_actor_links})
        parts.append(f"通过 {actor_count} 位共用演员产生关联")
    if co_star:
        parts.append(f"共同出演 {co_star} 部电影")
    return " · ".join(parts)


def _finalize_related_peers(
    peer_links: dict[str, list[dict[str, Any]]],
    role: str,
    limit: int,
) -> list[dict[str, Any]]:
    """按关联条数排序，组装相关影人卡片列表。"""
    scored: list[tuple[int, str, list[dict[str, Any]]]] = []
    for peer, links in peer_links.items():
        unique_links = _dedupe_links(links)
        if not unique_links:
            continue
        scored.append((len(unique_links), peer, unique_links))

    scored.sort(key=lambda item: (-item[0], item[1]))
    results: list[dict[str, Any]] = []
    for _, peer, links in scored[:limit]:
        sample = get_movies_by_filmmaker(peer, role, limit=FILMMAKER_SAMPLE_SIZE)
        results.append(
            {
                "name": peer,
                "movie_count": _peer_library_count(peer, role),
                "collaboration_count": len(links),
                "relation_summary": _build_relation_summary(links),
                "relation_types": sorted({link["type"] for link in links}),
                "links": links[:5],
                "sample_movies": sample,
                "poster_url": sample[0]["poster_url"] if sample else None,
            }
        )
    return results


def get_related_filmmakers(name: str, role: str, limit: int = RELATED_FILMMAKER_LIMIT) -> list[dict[str, Any]]:
    """
    详情页底部「相关导演/演员」。
    导演：共同执导(co_direct)、共用演员(shared_actor)
    演员：共同出演(co_star)
    """
    if role not in ("director", "actor"):
        return []

    column = "directors" if role == "director" else "actors"
    peer_links: dict[str, list[dict[str, Any]]] = defaultdict(list)

    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT movie_id, title, directors, actors FROM movies WHERE {column} LIKE %s",
                (f"%{name}%",),
            )
            subject_rows = cursor.fetchall()

    if role == "actor":
        # 演员详情：找同一部电影里出现过的其他演员
        for row in subject_rows:
            title = row["title"]
            movie_id = row["movie_id"]
            for peer in split_pipe(row["actors"]):
                if peer != name:
                    peer_links[peer].append(
                        {
                            "type": "co_star",
                            "type_label": "共同出演",
                            "movie_title": title,
                            "movie_id": movie_id,
                        }
                    )
        return _finalize_related_peers(peer_links, "actor", limit)

    # 导演详情：共同执导 + 通过共用演员关联的其他导演
    actor_to_subject_movies: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in subject_rows:
        title = row["title"]
        movie_id = row["movie_id"]
        for peer in split_pipe(row["directors"]):
            if peer != name:
                peer_links[peer].append(
                    {
                        "type": "co_direct",
                        "type_label": "共同执导",
                        "movie_title": title,
                        "movie_id": movie_id,
                    }
                )
        for actor in split_pipe(row["actors"]):
            actor_to_subject_movies[actor].append({"title": title, "movie_id": movie_id})

    # 取合作最多的 10 位演员，再找他们也合作过的其他导演
    top_actors = sorted(
        actor_to_subject_movies.keys(),
        key=lambda actor: len(actor_to_subject_movies[actor]),
        reverse=True,
    )[:10]

    if top_actors:
        with get_mysql() as conn:
            with conn.cursor() as cursor:
                for actor in top_actors:
                    cursor.execute(
                        "SELECT movie_id, title, directors FROM movies WHERE actors LIKE %s",
                        (f"%{actor}%",),
                    )
                    subject_movies = actor_to_subject_movies[actor][:2]
                    for row in cursor.fetchall():
                        peer_title = row["title"]
                        for peer in split_pipe(row["directors"]):
                            if peer == name:
                                continue
                            for subject_movie in subject_movies:
                                peer_links[peer].append(
                                    {
                                        "type": "shared_actor",
                                        "type_label": "共用演员",
                                        "via_actor": actor,
                                        "subject_movie_title": subject_movie["title"],
                                        "peer_movie_title": peer_title,
                                        "movie_title": peer_title,
                                        "movie_id": row["movie_id"],
                                    }
                                )

    return _finalize_related_peers(peer_links, "director", limit)


def get_filmmaker_detail(name: str, role: str, limit: int | None = None) -> dict[str, Any] | None:
    """
    影人详情页：姓名、作品列表、相关影人。
    前端 FilmmakerDetailView 调用 GET /api/charts/filmmaker/{role}/{name}。
    limit=None 时返回全部作品（按评分排序）。
    """
    if role not in ("director", "actor"):
        return None
    movies = get_movies_by_filmmaker(name, role, limit=limit, only_rated=False)
    if not movies:
        return None
    column = "directors" if role == "director" else "actors"
    total = 0
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT COUNT(*) AS total FROM movies WHERE {column} LIKE %s",
                (f"%{name}%",),
            )
            total = cursor.fetchone()["total"]
    return {
        "name": name,
        "role": role,
        "role_label": "导演" if role == "director" else "演员",
        "movie_count": total,
        "movies": movies,
        "related": get_related_filmmakers(name, role),
        "related_label": "相关导演" if role == "director" else "相关演员",
    }
