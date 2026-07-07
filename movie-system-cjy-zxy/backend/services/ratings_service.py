"""评分数据统一从 SQLite 读写；导出 NDJSON 仅供 Spark VM 同步。"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from config import FILMS_RATINGS_DIR, SPARK_DATA_DIR, SPARK_USER_OFFSET
from models import CrawledRating, UserRating, db


def _films_user_id(user_name: str) -> int:
    name = (user_name or "unknown").strip()
    return abs(hash(f"films::{name}")) % (2**31 - 1)


def _rating_csv_sources() -> list[Path]:
    if not FILMS_RATINGS_DIR.exists():
        return []
    return sorted(FILMS_RATINGS_DIR.glob("part-*.csv"))


def seed_crawled_ratings(force: bool = False) -> int:
    """将 films_data 爬虫评分 CSV 一次性导入 crawled_ratings 表（数据库为唯一数据源）。"""
    if not force and CrawledRating.query.count() > 0:
        return CrawledRating.query.count()

    csv_files = _rating_csv_sources()
    if not csv_files:
        return CrawledRating.query.count()

    if force:
        CrawledRating.query.delete()
        db.session.commit()

    batch: list[CrawledRating] = []
    for csv_path in csv_files:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                user_name = str(row.get("user_id", "")).strip()
                movie_id = str(row.get("movie_id", "")).strip()
                rating = float(row.get("rating") or 0)
                if not user_name or not movie_id or rating <= 0:
                    continue
                batch.append(
                    CrawledRating(
                        user_name=user_name,
                        movie_id=int(movie_id),
                        score=rating,
                        source=str(row.get("source") or "douban").strip() or "douban",
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


def build_spark_ratings_payload() -> tuple[list[dict], dict[str, int]]:
    """从数据库合并爬虫评分与网站用户评分，生成 Spark 所需结构。"""
    merged: dict[tuple[int, str], dict] = {}
    crawled_count = 0
    web_count = 0

    for item in CrawledRating.query.all():
        crawled_count += 1
        uid = _films_user_id(item.user_name)
        merged[(uid, str(item.movie_id))] = {
            "userId": uid,
            "movieId": str(item.movie_id),
            "rating": float(item.score),
        }

    for rating in UserRating.query.all():
        web_count += 1
        uid = SPARK_USER_OFFSET + rating.user_id
        merged[(uid, str(rating.movie_id))] = {
            "userId": uid,
            "movieId": str(rating.movie_id),
            "rating": float(rating.score),
        }

    payload = list(merged.values())
    stats = {
        "crawled_rows": crawled_count,
        "web_rows": web_count,
        "merged_total": len(payload),
    }
    return payload, stats


def export_spark_ratings_file(output_path: Path | None = None, *, ensure_seed: bool = True) -> int:
    """将数据库评分导出为 Spark NDJSON（VM 同步用，非持久数据源）。"""
    if ensure_seed and CrawledRating.query.count() == 0:
        seed_crawled_ratings()

    output_path = output_path or SPARK_DATA_DIR / "ratings.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload, stats = build_spark_ratings_payload()
    with output_path.open("w", encoding="utf-8") as handle:
        for row in payload:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(
        f"已导出 {stats['merged_total']} 条评分 -> {output_path} "
        f"(数据库 crawled: {stats['crawled_rows']}, web: {stats['web_rows']})"
    )
    return stats["merged_total"]
