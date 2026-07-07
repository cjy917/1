"""
【首页 H1/H3 + 详情 D0 + 问卷 A2】电影数据服务
MySQL 查询、首页分区、详情单条、问卷导演/演员选项
"""
import hashlib
import re
import threading
from contextlib import contextmanager
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from config import (
    BANNER_CANDIDATE_POOL,
    BANNER_EXCLUDED_MOVIE_IDS,
    BANNER_PRIORITY_MOVIE_IDS,
    BANNER_SIZE,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
    PICTURE_DIRS,
)
from services.language_utils import build_language_filter_options, language_match_aliases
from services.tmdb_meta import fetch_tmdb_overview, resolve_tmdb_id


def split_pipe(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split("|") if part.strip()]


@contextmanager
def get_mysql():
    conn = pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=DictCursor,
    )
    try:
        yield conn
    finally:
        conn.close()


def _row_to_movie(row: dict[str, Any]) -> dict[str, Any]:
    movie_id = row.get("movie_id")
    return {
        "id": row.get("id"),
        "movie_id": movie_id,
        "title": row.get("title"),
        "rating": row.get("rating") or 0,
        "rating_count": row.get("rating_count") or 0,
        "release_date": row.get("release_date"),
        "release_year": row.get("release_year") or 0,
        "directors": row.get("directors"),
        "writers": row.get("writers"),
        "actors": row.get("actors"),
        "aliases": row.get("aliases"),
        "summary": row.get("summary"),
        "detail_url": row.get("detail_url"),
        "languages": row.get("languages"),
        "genres": row.get("genres"),
        "duration": row.get("duration"),
        "reviews": row.get("reviews"),
        "countries": row.get("countries"),
        "awards": row.get("awards"),
        "review_count": row.get("review_count") or 0,
        "cover_path": row.get("cover_path"),
        "source": row.get("source"),
        "poster_url": f"/api/posters/{movie_id}" if movie_id else None,
        "genre_list": split_pipe(row.get("genres")),
        "director_list": split_pipe(row.get("directors")),
        "writer_list": split_pipe(row.get("writers")),
        "actor_list": split_pipe(row.get("actors")),
    }


def resolve_poster_file(movie_id: int | str, cover_path: str | None = None) -> str | None:
    candidates: list[str] = []
    if cover_path:
        normalized = cover_path.replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        candidates.append(normalized)
        candidates.append(normalized.split("/")[-1])
        if "posters/" in normalized:
            candidates.append(normalized.split("posters/", 1)[-1])
        if "picture/" in normalized:
            candidates.append(normalized.split("picture/", 1)[-1])
    candidates.append(f"{movie_id}.webp")
    candidates.append(f"{movie_id}.jpg")

    checked: set[str] = set()
    for name in candidates:
        filename = name.split("/")[-1]
        if not filename or filename in checked:
            continue
        checked.add(filename)
        for base in PICTURE_DIRS:
            path = base / filename
            if path.exists():
                return str(path)

    # TMDb 封面常见命名：{movie_id}_片名.jpg
    for base in PICTURE_DIRS:
        if not base.exists():
            continue
        for pattern in (f"{movie_id}_*.jpg", f"{movie_id}_*.webp", f"{movie_id}_*.jpeg"):
            matches = sorted(base.glob(pattern))
            if matches:
                return str(matches[0])
    return None


def _pick_movies_with_posters(
    where: str,
    order: str,
    limit: int,
    pool_size: int = 200,
) -> list[dict[str, Any]]:
    """从候选池中筛选本地封面存在的电影，避免「新上映」出现无封面项。"""
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM movies WHERE {where} ORDER BY {order} LIMIT %s",
                (pool_size,),
            )
            rows = cursor.fetchall()

    picked: list[dict[str, Any]] = []
    for row in rows:
        movie = _row_to_movie(row)
        if resolve_poster_file(movie["movie_id"], movie.get("cover_path")):
            picked.append(movie)
        if len(picked) >= limit:
            break
    return picked


def list_movies(
    page: int = 1,
    page_size: int = 20,
    genre: str | None = None,
    genres: list[str] | None = None,
    languages: list[str] | None = None,
    year: int | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    min_rating: float | None = None,
    max_rating: float | None = None,
    min_votes: int | None = None,
    keyword: str | None = None,
    sort: str = "rating_desc",
) -> dict[str, Any]:
    conditions: list[str] = ["1=1"]
    params: list[Any] = []

    selected_genres = [g for g in (genres or []) if g]
    if not selected_genres and genre:
        selected_genres = [genre]
    if selected_genres:
        genre_clauses = ["genres LIKE %s"] * len(selected_genres)
        conditions.append(f"({' OR '.join(genre_clauses)})")
        params.extend(f"%{item}%" for item in selected_genres)
    selected_languages = [lang for lang in (languages or []) if lang]
    if selected_languages:
        language_groups: list[str] = []
        for canonical in selected_languages:
            aliases = language_match_aliases(canonical)
            alias_clauses = ["languages LIKE %s"] * len(aliases)
            language_groups.append(f"({' OR '.join(alias_clauses)})")
            params.extend(f"%{alias}%" for alias in aliases)
        conditions.append(f"({' OR '.join(language_groups)})")
    if year:
        conditions.append("release_year = %s")
        params.append(year)
    if year_from is not None:
        conditions.append("release_year >= %s")
        params.append(year_from)
    if year_to is not None:
        conditions.append("release_year <= %s")
        params.append(year_to)
    if min_rating is not None:
        conditions.append("rating >= %s")
        params.append(min_rating)
    if max_rating is not None:
        conditions.append("rating <= %s")
        params.append(max_rating)
    if min_votes is not None and min_votes > 0:
        conditions.append("rating_count >= %s")
        params.append(min_votes)
    if keyword:
        conditions.append("(title LIKE %s OR actors LIKE %s OR directors LIKE %s OR aliases LIKE %s)")
        like = f"%{keyword}%"
        params.extend([like, like, like, like])

    order_map = {
        "rating_desc": "rating DESC, rating_count DESC",
        "rating_asc": "rating ASC, rating_count ASC",
        "year_desc": "release_year DESC, rating DESC",
        "year_asc": "release_year ASC, rating ASC",
        "popular": "rating_count DESC, rating DESC",
        "popular_asc": "rating_count ASC, rating ASC",
        "latest": "release_year DESC, rating DESC",
    }
    order_by = order_map.get(sort, order_map["rating_desc"])
    where_sql = " AND ".join(conditions)
    offset = (page - 1) * page_size

    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM movies WHERE {where_sql}", params)
            total = cursor.fetchone()["total"]
            cursor.execute(
                f"""
                SELECT * FROM movies
                WHERE {where_sql}
                ORDER BY {order_by}
                LIMIT %s OFFSET %s
                """,
                [*params, page_size, offset],
            )
            rows = cursor.fetchall()

    return {
        "items": [_row_to_movie(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size if page_size else 0,
    }


def get_movie_by_id(movie_id: int) -> dict[str, Any] | None:
    """【详情 D0】MySQL 单条电影 → 前端 detail 页主数据"""
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM movies WHERE movie_id = %s LIMIT 1", (movie_id,))
            row = cursor.fetchone()
    return _row_to_movie(row) if row else None


def _summary_looks_incomplete(text: str | None) -> bool:
    summary = (text or "").strip()
    if not summary:
        return True
    if summary[-1] in "。！？…!?.":
        return False
    return len(summary) >= 60


def _fetch_longest_summary_from_db(movie_id: int | str, title: str) -> str | None:
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT summary
                FROM movies
                WHERE summary IS NOT NULL
                  AND summary != ''
                  AND (movie_id = %s OR title = %s)
                ORDER BY CHAR_LENGTH(summary) DESC
                LIMIT 1
                """,
                (movie_id, title),
            )
            row = cursor.fetchone()
    if not row:
        return None
    return (row.get("summary") or "").strip() or None


def _persist_summary(movie_id: int | str, summary: str) -> None:
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE movies
                SET summary = %s
                WHERE movie_id = %s
                  AND (summary IS NULL OR CHAR_LENGTH(summary) < %s)
                """,
                (summary, movie_id, len(summary)),
            )
        conn.commit()


def apply_local_summary(movie: dict[str, Any]) -> dict[str, Any]:
    """仅使用本地数据库中的更长简介，不请求外部接口。"""
    summary = (movie.get("summary") or "").strip()
    alt_summary = _fetch_longest_summary_from_db(movie.get("movie_id"), (movie.get("title") or "").strip())
    if alt_summary and len(alt_summary) > len(summary):
        return {**movie, "summary": alt_summary}
    return movie


_summary_enrich_attempted: set[int | str] = set()


def schedule_summary_enrich(movie_id: int | str) -> None:
    """后台补全简介，避免拖慢详情页首屏。"""
    if movie_id in _summary_enrich_attempted:
        return

    def task() -> None:
        try:
            movie = get_movie_by_id(int(movie_id))
            if not movie or not _summary_looks_incomplete(movie.get("summary")):
                _summary_enrich_attempted.add(movie_id)
                return
            enrich_movie_summary(movie)
        finally:
            _summary_enrich_attempted.add(movie_id)

    threading.Thread(target=task, daemon=True).start()


def enrich_movie_summary(movie: dict[str, Any]) -> dict[str, Any]:
    """补全爬虫阶段被截断的剧情简介，并写回数据库避免重复请求。"""
    movie = apply_local_summary(movie)
    summary = (movie.get("summary") or "").strip()
    movie_id = movie.get("movie_id")
    original = summary

    if not _summary_looks_incomplete(summary):
        return movie

    tmdb_id = resolve_tmdb_id(
        movie_id,
        (movie.get("title") or "").strip(),
        movie.get("aliases") or "",
        movie.get("release_year"),
        movie.get("detail_url"),
    )
    overview = fetch_tmdb_overview(tmdb_id) if tmdb_id else None
    if overview and len(overview) > len(summary):
        summary = overview

    if summary != original:
        _persist_summary(movie_id, summary)
        return {**movie, "summary": summary}
    return movie


def search_suggest(keyword: str, limit: int = 8) -> list[dict[str, Any]]:
    if not keyword.strip():
        return []
    like = f"%{keyword.strip()}%"
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT movie_id, title, rating, release_year, genres
                FROM movies
                WHERE title LIKE %s OR aliases LIKE %s
                ORDER BY rating_count DESC, rating DESC
                LIMIT %s
                """,
                (like, like, limit),
            )
            rows = cursor.fetchall()
    return [
        {
            "movie_id": row["movie_id"],
            "title": row["title"],
            "rating": row["rating"],
            "release_year": row["release_year"],
            "genres": row["genres"],
            "poster_url": f"/api/posters/{row['movie_id']}",
        }
        for row in rows
    ]


def _pick_banner_movies() -> list[dict[str, Any]]:
    reserve = len(BANNER_PRIORITY_MOVIE_IDS)
    target_core = max(BANNER_SIZE - reserve, 0)

    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT * FROM movies
                WHERE rating >= 8 AND rating_count >= 1000
                ORDER BY rating DESC, rating_count DESC
                LIMIT %s
                """,
                (BANNER_CANDIDATE_POOL,),
            )
            rows = cursor.fetchall()

    picked: list[dict[str, Any]] = []
    picked_ids: set[int] = set()
    for row in rows:
        movie_id = row.get("movie_id")
        if movie_id in BANNER_EXCLUDED_MOVIE_IDS or movie_id in picked_ids:
            continue
        if not resolve_poster_file(movie_id, row.get("cover_path")):
            continue
        picked.append(_row_to_movie(row))
        picked_ids.add(int(movie_id))
        if len(picked) >= target_core:
            break

    if reserve:
        with get_mysql() as conn:
            with conn.cursor() as cursor:
                for movie_id in BANNER_PRIORITY_MOVIE_IDS:
                    if len(picked) >= BANNER_SIZE:
                        break
                    if int(movie_id) in picked_ids:
                        continue
                    cursor.execute("SELECT * FROM movies WHERE movie_id = %s", (movie_id,))
                    row = cursor.fetchone()
                    if not row:
                        continue
                    if not resolve_poster_file(movie_id, row.get("cover_path")):
                        continue
                    picked.append(_row_to_movie(row))
                    picked_ids.add(int(movie_id))

    return picked[:BANNER_SIZE]


def get_home_trailer_targets() -> list[dict[str, Any]]:
    """首页 Hero + 热门电影栏（前 POPULAR_TRAILER_DOWNLOAD_SIZE 部），去重。"""
    from config import POPULAR_TRAILER_DOWNLOAD_SIZE

    sections = get_home_sections()
    seen: set[int] = set()
    movies: list[dict[str, Any]] = []

    for movie in sections.get("banner", []):
        movie_id = int(movie["movie_id"])
        if movie_id in seen:
            continue
        seen.add(movie_id)
        movies.append(movie)

    popular_added = 0
    for movie in sections.get("popular", []):
        if popular_added >= POPULAR_TRAILER_DOWNLOAD_SIZE:
            break
        movie_id = int(movie["movie_id"])
        if movie_id in seen:
            continue
        seen.add(movie_id)
        movies.append(movie)
        popular_added += 1

    return movies


def get_home_sections() -> dict[str, list[dict[str, Any]]]:
    """【首页 H1/H3】banner + popular + top_rated + latest 四个分区"""
    sections = {"banner": _pick_banner_movies()}
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            for key, (where, order, limit) in {
                "popular": ("rating_count >= 500", "rating_count DESC", 20),
                "top_rated": ("rating >= 7.5 AND rating_count >= 100", "rating DESC", 20),
            }.items():
                cursor.execute(
                    f"SELECT * FROM movies WHERE {where} ORDER BY {order} LIMIT %s",
                    (limit,),
                )
                sections[key] = [_row_to_movie(row) for row in cursor.fetchall()]

    # 新上映：按年份从新到旧逐层选取，且必须有本地封面
    latest: list[dict[str, Any]] = []
    for year in range(2026, 2014, -1):
        if len(latest) >= 20:
            break
        batch = _pick_movies_with_posters(
            f"release_year = {year} AND rating > 0",
            "rating DESC, rating_count DESC",
            limit=20 - len(latest),
            pool_size=80,
        )
        latest.extend(batch)
    sections["latest"] = latest
    return sections


def get_filter_options() -> dict[str, list[Any]]:
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT release_year FROM movies WHERE release_year > 0 ORDER BY release_year DESC"
            )
            years = [row["release_year"] for row in cursor.fetchall()]
            cursor.execute("SELECT genres FROM movies WHERE genres IS NOT NULL AND genres != ''")
            genre_counter: dict[str, int] = {}
            for row in cursor.fetchall():
                for genre in split_pipe(row["genres"]):
                    genre_counter[genre] = genre_counter.get(genre, 0) + 1
            cursor.execute("SELECT languages FROM movies WHERE languages IS NOT NULL AND languages != ''")
            language_rows = [row["languages"] for row in cursor.fetchall()]
    genres = sorted(genre_counter.items(), key=lambda x: (-x[1], x[0]))
    return {
        "years": years,
        "genres": [name for name, _ in genres[:40]],
        "languages": build_language_filter_options(language_rows),
    }


def get_movies_by_ids(movie_ids: list[int]) -> list[dict[str, Any]]:
    if not movie_ids:
        return []
    placeholders = ",".join(["%s"] * len(movie_ids))
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM movies WHERE movie_id IN ({placeholders})",
                movie_ids,
            )
            rows = cursor.fetchall()
    row_map = {row["movie_id"]: _row_to_movie(row) for row in rows}
    return [row_map[mid] for mid in movie_ids if mid in row_map]


def get_similar_movies(movie_id: int, limit: int = 12) -> list[dict[str, Any]]:
    base = get_movie_by_id(movie_id)
    if not base:
        return []

    genres = base.get("genre_list") or []
    directors = base.get("director_list") or []
    if not genres:
        with get_mysql() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT * FROM movies
                    WHERE movie_id != %s AND genres IS NOT NULL
                    ORDER BY rating DESC
                    LIMIT %s
                    """,
                    (movie_id, limit),
                )
                return [_row_to_movie(row) for row in cursor.fetchall()]

    genre_like = " OR ".join(["genres LIKE %s"] * len(genres))
    params: list[Any] = [movie_id, *[f"%{g}%" for g in genres], limit]
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT * FROM movies
                WHERE movie_id != %s AND ({genre_like})
                ORDER BY rating DESC, rating_count DESC
                LIMIT %s
                """,
                params,
            )
            rows = cursor.fetchall()

    scored = []
    base_genres = set(genres)
    base_directors = set(directors)
    for row in rows:
        movie = _row_to_movie(row)
        overlap = len(base_genres & set(movie.get("genre_list") or []))
        director_overlap = len(base_directors & set(movie.get("director_list") or []))
        score = overlap * 2 + director_overlap * 3 + (movie.get("rating") or 0) * 0.1
        scored.append((score, movie))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def poster_color(title: str) -> str:
    digest = hashlib.md5(title.encode("utf-8")).hexdigest()
    return f"#{digest[:6]}"


def _strip_review_metadata(content: str) -> str:
    """Remove duplicated 作者/评分 prefix embedded in crawled review text."""
    stripped = re.sub(
        r"^作者:\s*[^|]+\|\s*评分:\s*[\d.]+/10(?:（[^）]*）)?\s*",
        "",
        content,
        count=1,
    ).strip()
    if stripped:
        return stripped
    match = re.search(r"评分:\s*[\d.]+/10(?:（[^）]*）)?\s*(.+)$", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content.strip()


def parse_crawled_reviews(reviews_text: str | None) -> list[dict[str, Any]]:
    if not reviews_text:
        return []
    items = []
    for part in reviews_text.split("[评论")[1:]:
        idx_end = part.find("]")
        if idx_end == -1:
            continue
        raw = part[idx_end + 1 :].strip()
        author_match = re.search(r"作者:\s*([^|]+)", raw)
        rating_match = re.search(r"评分:\s*([\d.]+)/10", raw)
        if author_match:
            items.append(
                {
                    "author": author_match.group(1).strip(),
                    "rating": float(rating_match.group(1)) if rating_match else None,
                    "content": _strip_review_metadata(raw),
                }
            )
    return items[:5]
