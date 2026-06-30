"""
电影数据服务模块

【核心职责】
通过 PyMySQL 直接查询 MySQL 中的 movies 表（未在 models.py 中定义）

【movies 表说明】
  - 表结构定义在：../../movies_backup.sql
  - 数据量：6766部电影，22个字段
  - 查询方式：PyMySQL 直接查询（非 SQLAlchemy ORM）
  - 原因：数据量大、字段多、需全文检索，SQLite 性能不足

【调用方】
  - recommend_service.py：获取推荐电影详情
  - recommendation_service.py：获取推荐电影详情、相似电影
  - analytics_service.py：获取电影数据进行统计分析

【海报路径优先级】（按 config.py 中 PICTURE_DIRS 配置顺序）
  1. posters/
  2. posters/posters/
  3. picture/
  4. picture/output/posters/
  5. films_data/picture/
  6. movie-system/picture/
"""

import hashlib
import re
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


def split_pipe(value: str | None) -> list[str]:
    """
    按 | 分割多值字段
    
    Args:
        value: 以 | 分隔的字符串
    
    Returns:
        分割后的字符串列表（去除空值和首尾空格）
    """
    if not value:
        return []
    return [part.strip() for part in value.split("|") if part.strip()]


@contextmanager
def get_mysql():
    """
    获取 MySQL 连接（上下文管理器）
    
    Yields:
        pymysql.Connection：MySQL 连接对象
    
    配置来源：
        config.py 中的 MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
    """
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
    """
    将 MySQL 查询行转换为电影字典（统一格式）
    
    Args:
        row: MySQL 查询结果行
    
    Returns:
        电影字典（含 movie_id, title, rating, poster_url 等完整字段）
    
    转换规则：
        - rating/rating_count/release_year/review_count 为空时默认 0
        - genres/directors/actors 分割为列表
        - poster_url 生成 API 路径
    """
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
        "actor_list": split_pipe(row.get("actors")),
    }


def resolve_poster_file(movie_id: int | str, cover_path: str | None = None) -> str | None:
    """
    解析电影海报文件路径
    
    Args:
        movie_id: 电影ID
        cover_path: 封面路径（来自数据库）
    
    Returns:
        海报文件的绝对路径（找不到返回 None）
    
    搜索顺序：
        1. cover_path 指定的路径（多种变体）
        2. {movie_id}.webp / {movie_id}.jpg
        3. {movie_id}_片名.jpg / .webp（TMDb 常见命名）
    
    搜索目录（按优先级）：
        PICTURE_DIRS 配置的 5 个目录
    """
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
    """
    从候选池中筛选有本地封面的电影
    
    Args:
        where: WHERE 条件
        order: ORDER BY 条件
        limit: 返回数量
        pool_size: 候选池大小
    
    Returns:
        有本地封面的电影列表
    
    用途：
        「新上映」栏目等需要展示封面的场景，避免出现无封面项
    """
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
    """
    电影列表查询（支持多条件筛选和分页）
    
    Args:
        page: 页码（从1开始）
        page_size: 每页数量
        genre/genres: 类型筛选
        languages: 语言筛选
        year/year_from/year_to: 年份筛选
        min_rating/max_rating: 评分范围筛选
        min_votes: 最低评价人数
        keyword: 搜索关键词（标题/演员/导演/别名）
        sort: 排序方式
    
    Returns:
        {items: 电影列表, total: 总数, page: 当前页, page_size: 每页数量, pages: 总页数}
    
    排序方式：
        - rating_desc: 评分降序（默认）
        - rating_asc: 评分升序
        - year_desc: 年份降序
        - year_asc: 年份升序
        - popular: 热门度（评价人数降序）
        - latest: 最新上映
    """
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
    """
    根据电影ID获取电影详情
    
    Args:
        movie_id: 电影ID
    
    Returns:
        电影详情字典（找不到返回 None）
    
    调用链：
        recommendation_service.py → get_movie_by_id() → MySQL movies 表
    """
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM movies WHERE movie_id = %s LIMIT 1", (movie_id,))
            row = cursor.fetchone()
    return _row_to_movie(row) if row else None


def search_suggest(keyword: str, limit: int = 8) -> list[dict[str, Any]]:
    """
    搜索建议（按标题/别名匹配）
    
    Args:
        keyword: 搜索关键词
        limit: 返回数量
    
    Returns:
        搜索建议列表（含 movie_id, title, rating, release_year, genres, poster_url）
    """
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
    """
    选取首页 Banner 轮播电影
    
    Returns:
        Banner 电影列表（数量由 BANNER_SIZE 控制）
    
    选取逻辑：
        1. 优先选取 BANNER_PRIORITY_MOVIE_IDS 指定的电影
        2. 从高分电影池中（rating >= 8, rating_count >= 1000）补充
        3. 必须有本地封面
    """
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
    """
    获取首页需要下载预告片的电影列表
    
    Returns:
        Banner + 热门电影列表（去重）
    
    用途：
        脚本下载预告片时确定目标电影
    """
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
    """
    获取首页各栏目数据
    
    Returns:
        {banner: Banner电影, popular: 热门电影, top_rated: 高分电影, latest: 新上映电影}
    
    各栏目规则：
        - banner: 高分电影（rating >= 8）+ 优先级电影，需有封面
        - popular: 评价人数 >= 500，按评价人数降序
        - top_rated: 评分 >= 7.5 且评价人数 >= 100，按评分降序
        - latest: 按年份从新到旧，需有封面
    """
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
    """
    获取筛选选项（年份、类型、语言）
    
    Returns:
        {years: 年份列表, genres: 类型列表, languages: 语言选项}
    
    用途：
        前端筛选组件的下拉选项数据
    """
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
    """
    根据电影ID列表批量获取电影详情
    
    Args:
        movie_ids: 电影ID列表
    
    Returns:
        电影详情列表（保持原始顺序）
    
    调用链：
        recommend_service.py → get_movies_by_ids() → MySQL movies 表
        recommendation_service.py → get_movies_by_ids() → MySQL movies 表
    
    注意：返回结果按输入顺序排列，不在数据库中的电影会被跳过
    """
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
    """
    获取相似电影（基于类型和导演）
    
    Args:
        movie_id: 基准电影ID
        limit: 返回数量
    
    Returns:
        相似电影列表（按相似度降序）
    
    相似度算法：
        score = 类型重叠数 × 2 + 导演重叠数 × 3 + 评分 × 0.1
    
    调用链：
        recommend_service.py → get_similar_movies() → MySQL movies 表
        recommendation_service.py → get_similar_movies() → MySQL movies 表
    """
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
    """
    根据电影标题生成海报背景色（哈希值）
    
    Args:
        title: 电影标题
    
    Returns:
        十六进制颜色代码（#RRGGBB）
    
    用途：
        海报加载失败时的占位背景色
    """
    digest = hashlib.md5(title.encode("utf-8")).hexdigest()
    return f"#{digest[:6]}"


def _strip_review_metadata(content: str) -> str:
    """去除爬虫评论文本中嵌入的作者/评分前缀"""
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
    """
    解析爬虫评论数据
    
    Args:
        reviews_text: 爬虫获取的评论文本（格式：[评论N]作者:xxx|评分:x.x/10 内容）
    
    Returns:
        评论列表（最多5条，含 author, rating, content）
    """
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