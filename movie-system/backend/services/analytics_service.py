from collections import Counter
import re
from typing import Any

from services.country_utils import (
    build_country_filter_options,
    country_match_aliases,
    extract_canonical_countries,
)
from services.language_utils import extract_canonical_languages
from services.movie_service import get_mysql, split_pipe

_DURATION_RE = re.compile(r"(\d+)")


def parse_duration_minutes(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        mins = int(value)
        return mins if mins > 0 else None
    text = str(value).strip()
    if not text:
        return None
    match = _DURATION_RE.search(text)
    if match:
        return int(match.group(1))
    return None


def _parse_filters(genre: str | None = None, year: str | None = None, country: str | None = None) -> tuple[str, list[Any]]:
    conditions: list[str] = []
    params: list[Any] = []

    if genre:
        genre_list = [g.strip() for g in genre.split(",") if g.strip()]
        if genre_list:
            parts = ["genres LIKE %s" for _ in genre_list]
            params.extend(f"%{g}%" for g in genre_list)
            conditions.append("(" + " OR ".join(parts) + ")")

    if year:
        year_tokens = [y.strip() for y in year.split(",") if y.strip()]
        year_parts: list[str] = []
        numeric_years: list[int] = []
        for token in year_tokens:
            if token == "更早":
                year_parts.append("(release_year > 0 AND release_year < %s)")
                params.append(2010)
            else:
                try:
                    numeric_years.append(int(token))
                except ValueError:
                    continue
        if numeric_years:
            placeholders = ",".join(["%s"] * len(numeric_years))
            year_parts.append(f"release_year IN ({placeholders})")
            params.extend(numeric_years)
        if year_parts:
            conditions.append("(" + " OR ".join(year_parts) + ")")

    if country:
        country_list = [c.strip() for c in country.split(",") if c.strip()]
        if country_list:
            parts: list[str] = []
            for canonical in country_list:
                for alias in country_match_aliases(canonical):
                    parts.append("countries LIKE %s")
                    params.append(f"%{alias}%")
            conditions.append("(" + " OR ".join(parts) + ")")

    where = " AND ".join(conditions) if conditions else "1=1"
    return where, params


def _fetch_column(column: str, genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    where, params = _parse_filters(genre, year, country)
    sql = f"SELECT {column} FROM movies WHERE {where} AND {column} IS NOT NULL AND {column} != ''"
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()


def _movie_row(row: dict[str, Any]) -> dict[str, Any]:
    directors = row.get("directors") or ""
    director = split_pipe(directors)[0] if directors else None
    countries = row.get("countries") or ""
    country = split_pipe(countries)[0] if countries else None
    languages = row.get("languages") or ""
    language = split_pipe(languages)[0] if languages else None
    return {
        "movie_id": row.get("movie_id"),
        "title": row.get("title"),
        "rating": float(row["rating"]) if row.get("rating") else None,
        "rating_count": int(row.get("rating_count") or 0),
        "genres": row.get("genres"),
        "year": row.get("release_year"),
        "director": director,
        "duration": row.get("duration"),
        "country": country,
        "language": language,
        "summary": row.get("summary"),
        "awards": row.get("awards"),
    }


def genre_distribution(limit: int = 15, genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for row in _fetch_column("genres", genre, year, country):
        for name in split_pipe(row["genres"]):
            counter[name] += 1
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def year_distribution(genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    where, params = _parse_filters(genre, year, country)
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT release_year AS year, COUNT(*) AS count
                FROM movies
                WHERE {where} AND release_year > 0
                GROUP BY release_year
                ORDER BY release_year
                """,
                params,
            )
            return cursor.fetchall()


def country_distribution(limit: int = 12, genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for row in _fetch_column("countries", genre, year, country):
        for name in extract_canonical_countries(row["countries"]):
            counter[name] += 1
    return [{"name": name, "value": count} for name, count in counter.most_common(limit)]


def analytics_filter_options(
    genre_limit: int = 25,
    country_limit: int = 20,
    year_from: int = 2010,
) -> dict[str, list[Any]]:
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT release_year FROM movies
                WHERE release_year >= %s
                ORDER BY release_year DESC
                """,
                (year_from,),
            )
            years = [row["release_year"] for row in cursor.fetchall()]
            cursor.execute(
                "SELECT COUNT(*) AS c FROM movies WHERE release_year > 0 AND release_year < %s",
                (year_from,),
            )
            if cursor.fetchone()["c"] > 0:
                years.append("更早")
            cursor.execute("SELECT genres FROM movies WHERE genres IS NOT NULL AND genres != ''")
            genre_counter: Counter[str] = Counter()
            for row in cursor.fetchall():
                for name in split_pipe(row["genres"]):
                    genre_counter[name] += 1
            cursor.execute("SELECT countries FROM movies WHERE countries IS NOT NULL AND countries != ''")
            country_rows = [row["countries"] for row in cursor.fetchall()]
    return {
        "genres": [name for name, _ in genre_counter.most_common(genre_limit)],
        "years": years,
        "countries": build_country_filter_options(country_rows, country_limit),
    }


def rating_distribution(genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    buckets = {"0-4": 0, "4-6": 0, "6-7": 0, "7-8": 0, "8-10": 0}
    where, params = _parse_filters(genre, year, country)
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT rating FROM movies WHERE {where} AND rating IS NOT NULL", params)
            for row in cursor.fetchall():
                score = row["rating"] or 0
                if score < 4:
                    buckets["0-4"] += 1
                elif score < 6:
                    buckets["4-6"] += 1
                elif score < 7:
                    buckets["6-7"] += 1
                elif score < 8:
                    buckets["7-8"] += 1
                else:
                    buckets["8-10"] += 1
    return [{"range": key, "count": value} for key, value in buckets.items()]


def rating_histogram() -> list[dict[str, Any]]:
    bins = {f"{i}": 0 for i in range(1, 11)}
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT rating FROM movies WHERE rating > 0")
            for row in cursor.fetchall():
                key = str(min(10, max(1, int(round(row["rating"])))))
                bins[key] += 1
    return [{"score": k, "count": v} for k, v in bins.items()]


def top_movies(limit: int = 12, genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    where, params = _parse_filters(genre, year, country)
    params.append(limit)
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT movie_id, title, rating, rating_count, genres, release_year, directors, duration
                FROM movies
                WHERE {where} AND rating > 0
                ORDER BY rating DESC, rating_count DESC
                LIMIT %s
                """,
                params,
            )
            return [_movie_row(row) for row in cursor.fetchall()]


def featured_movies(limit: int = 12, genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    where, params = _parse_filters(genre, year, country)
    params.append(limit)
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT movie_id, title, rating, rating_count, genres, release_year, directors, duration
                FROM movies
                WHERE {where} AND rating > 0 AND rating_count > 100
                ORDER BY RAND()
                LIMIT %s
                """,
                params,
            )
            return [_movie_row(row) for row in cursor.fetchall()]


def get_all_movies(limit: int = 500, genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    where, params = _parse_filters(genre, year, country)
    params.append(limit)
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT movie_id, title, rating, rating_count, genres, release_year,
                       directors, duration, countries, languages, summary, awards
                FROM movies
                WHERE {where} AND rating > 0
                ORDER BY rating DESC, rating_count DESC
                LIMIT %s
                """,
                params,
            )
            return [_movie_row(row) for row in cursor.fetchall()]


def actor_wordcloud(limit: int = 40) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT actors FROM movies WHERE actors IS NOT NULL AND actors != ''")
            for row in cursor.fetchall():
                for actor in split_pipe(row["actors"]):
                    if actor and actor != "未知":
                        counter[actor] += 1
    return [{"name": name, "value": count} for name, count in counter.most_common(limit)]


def actor_distribution(limit: int = 10, genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for row in _fetch_column("actors", genre, year, country):
        for name in split_pipe(row["actors"]):
            if name and name != "未知" and len(name) > 1:
                counter[name] += 1
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def source_distribution() -> list[dict[str, Any]]:
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT source AS name, COUNT(*) AS value
                FROM movies
                GROUP BY source
                """
            )
            return cursor.fetchall()


def rating_leaderboard(limit: int = 10) -> list[dict[str, Any]]:
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT movie_id, title, rating, rating_count, release_year
                FROM movies
                WHERE rating > 0 AND rating_count > 100
                ORDER BY rating_count DESC, rating DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cursor.fetchall()
    return [
        {
            "movie_id": row["movie_id"],
            "title": row["title"],
            "rating": round(float(row["rating"] or 0), 1),
            "rating_count": int(row["rating_count"] or 0),
            "release_year": row["release_year"],
            "poster_url": f"/api/posters/{row['movie_id']}",
        }
        for row in rows
    ]


def overview_stats(
    genre: str | None = None,
    year: str | None = None,
    country: str | None = None,
    user_count: int = 0,
    rating_count: int = 0,
) -> dict[str, Any]:
    where, params = _parse_filters(genre, year, country)
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS total FROM movies WHERE {where}", params)
            total_movies = cursor.fetchone()["total"]
            cursor.execute(
                f"SELECT AVG(rating) AS avg_rating FROM movies WHERE {where} AND rating > 0",
                params,
            )
            avg_rating = cursor.fetchone()["avg_rating"] or 0
            cursor.execute(
                f"SELECT COALESCE(SUM(rating_count), 0) AS total FROM movies WHERE {where}",
                params,
            )
            total_ratings = int(cursor.fetchone()["total"] or 0)
            cursor.execute(
                f"SELECT COALESCE(SUM(review_count), 0) AS total FROM movies WHERE {where}",
                params,
            )
            total_reviews = int(cursor.fetchone()["total"] or 0)
            cursor.execute(
                f"""
                SELECT COUNT(*) AS total FROM movies
                WHERE {where} AND reviews IS NOT NULL AND reviews != ''
                """,
                params,
            )
            with_reviews = cursor.fetchone()["total"]
    return {
        "total_movies": total_movies,
        "total_users": user_count,
        "total_ratings": total_ratings,
        "total_reviews": total_reviews,
        "avg_rating": round(float(avg_rating), 2),
        "movies_with_reviews": with_reviews,
    }


def language_distribution(limit: int = 10, genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for row in _fetch_column("languages", genre, year, country):
        for name in extract_canonical_languages(row["languages"]):
            counter[name] += 1
    return [{"name": name, "value": count} for name, count in counter.most_common(limit)]


def duration_distribution(genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    buckets = {"60分钟以下": 0, "60-90分钟": 0, "90-120分钟": 0, "120-150分钟": 0, "150分钟以上": 0}
    where, params = _parse_filters(genre, year, country)
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT duration FROM movies WHERE {where} AND duration IS NOT NULL AND duration != ''",
                params,
            )
            for row in cursor.fetchall():
                mins = parse_duration_minutes(row["duration"])
                if not mins:
                    continue
                if mins < 60:
                    buckets["60分钟以下"] += 1
                elif mins < 90:
                    buckets["60-90分钟"] += 1
                elif mins < 120:
                    buckets["90-120分钟"] += 1
                elif mins < 150:
                    buckets["120-150分钟"] += 1
                else:
                    buckets["150分钟以上"] += 1
    return [{"range": key, "count": value} for key, value in buckets.items()]


def director_distribution(limit: int = 10, genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for row in _fetch_column("directors", genre, year, country):
        for name in split_pipe(row["directors"]):
            if name and len(name) > 1:
                counter[name] += 1
    return [{"name": name, "count": count} for name, count in counter.most_common(limit)]


def review_count_distribution(genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    buckets = {"0-100": 0, "100-500": 0, "500-1000": 0, "1000-5000": 0, "5000+": 0}
    where, params = _parse_filters(genre, year, country)
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT review_count FROM movies WHERE {where} AND review_count IS NOT NULL",
                params,
            )
            for row in cursor.fetchall():
                rc = int(row["review_count"] or 0)
                if rc < 100:
                    buckets["0-100"] += 1
                elif rc < 500:
                    buckets["100-500"] += 1
                elif rc < 1000:
                    buckets["500-1000"] += 1
                elif rc < 5000:
                    buckets["1000-5000"] += 1
                else:
                    buckets["5000+"] += 1
    return [{"range": key, "count": value} for key, value in buckets.items()]


def country_genre_correlation(limit: int = 8, genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    where, params = _parse_filters(genre, year, country)
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT countries, genres FROM movies
                WHERE {where}
                  AND countries IS NOT NULL AND countries != ''
                  AND genres IS NOT NULL AND genres != ''
                """,
                params,
            )
            for row in cursor.fetchall():
                countries = split_pipe(row["countries"])[:2]
                genres = split_pipe(row["genres"])[:3]
                for country_name in countries:
                    for genre_name in genres:
                        counter[f"{country_name}-{genre_name}"] += 1
    return [{"name": key, "value": count} for key, count in counter.most_common(limit)]


def rating_duration_correlation(genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    where, params = _parse_filters(genre, year, country)
    results: list[dict[str, Any]] = []
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT rating, duration FROM movies
                WHERE {where}
                  AND rating > 0
                  AND duration IS NOT NULL AND duration != ''
                LIMIT 500
                """,
                params,
            )
            for row in cursor.fetchall():
                mins = parse_duration_minutes(row["duration"])
                if not mins:
                    continue
                results.append({"rating": float(row["rating"]), "duration": mins})
                if len(results) >= 200:
                    break
    return results


def award_distribution(limit: int = 10, genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for row in _fetch_column("awards", genre, year, country):
        awards_text = (row["awards"] or "").strip()
        if not awards_text:
            continue
        if "获奖" in awards_text or "提名" in awards_text:
            counter["有获奖/提名"] += 1
        else:
            counter["无"] += 1
    return [{"name": name, "value": count} for name, count in counter.most_common(limit)]


def wordcloud_data(limit: int = 60, genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    """单类型 + 2~3 标签的真实组合，控制词条数量。"""
    single_counter: Counter[str] = Counter()
    signature_counter: Counter[str] = Counter()
    for row in _fetch_column("genres", genre, year, country):
        tags = sorted({tag for tag in split_pipe(row["genres"]) if tag})
        if not tags:
            continue
        for tag in tags:
            single_counter[tag] += 1
        if 2 <= len(tags) <= 3:
            signature_counter["|".join(tags)] += 1

    single_limit = min(12, limit)
    signature_limit = max(limit - single_limit, 0)
    ranked = sorted(
        single_counter.most_common(single_limit) + signature_counter.most_common(signature_limit),
        key=lambda item: item[1],
        reverse=True,
    )[:limit]
    return [{"name": name, "value": count} for name, count in ranked]


def monthly_release_distribution(genre: str | None = None, year: str | None = None, country: str | None = None) -> list[dict[str, Any]]:
    where, params = _parse_filters(genre, year, country)
    month_names = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]
    result = {name: 0 for name in month_names}
    with get_mysql() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT MONTH(release_date) AS month, COUNT(*) AS count
                FROM movies
                WHERE {where}
                  AND release_date IS NOT NULL
                  AND release_date != ''
                  AND MONTH(release_date) IS NOT NULL
                GROUP BY MONTH(release_date)
                ORDER BY MONTH(release_date)
                """,
                params,
            )
            for row in cursor.fetchall():
                month = row.get("month")
                if month is None:
                    continue
                idx = int(month) - 1
                if 0 <= idx < 12:
                    result[month_names[idx]] = row["count"]
    return [{"month": key, "count": value} for key, value in result.items()]
