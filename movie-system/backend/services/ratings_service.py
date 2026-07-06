"""评分数据统一从 SQLite 读写；导出 NDJSON 仅供 Spark VM 同步。"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from config import (
    FILMS_RATINGS_DIR,
    SPARK_DATA_DIR,
    SPARK_HISTORY_RATINGS,
    SPARK_USER_OFFSET,
    SPARK_WEB_RATINGS,
)
from models import CrawledRating, UserRating, db


def _films_user_id(user_name: str) -> int:
    name = (user_name or "unknown").strip()
    return abs(hash(f"films::{name}")) % (2**31 - 1)


def _write_ndjson_rows(rows: list[dict], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


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


def build_spark_history_payload() -> tuple[list[dict], dict[str, int]]:
    """历史爬虫评分（部署后基本不变，可预导出到 VM）。"""
    merged: dict[tuple[int, str], dict] = {}
    crawled_count = 0

    for item in CrawledRating.query.all():
        crawled_count += 1
        uid = _films_user_id(item.user_name)
        merged[(uid, str(item.movie_id))] = {
            "userId": uid,
            "movieId": str(item.movie_id),
            "rating": float(item.score),
        }

    payload = list(merged.values())
    stats = {
        "crawled_rows": crawled_count,
        "merged_total": len(payload),
    }
    return payload, stats


def build_spark_web_payload() -> tuple[list[dict], dict[str, int]]:
    """网站用户评分（刷新时增量同步）。"""
    merged: dict[tuple[int, str], dict] = {}
    web_count = 0

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
        "web_rows": web_count,
        "merged_total": len(payload),
    }
    return payload, stats


def build_spark_ratings_payload() -> tuple[list[dict], dict[str, int]]:
    """从数据库合并爬虫评分与网站用户评分，生成 Spark 所需结构。"""
    history, history_stats = build_spark_history_payload()
    web, web_stats = build_spark_web_payload()
    merged: dict[tuple[int, str], dict] = {}
    for row in history:
        merged[(row["userId"], row["movieId"])] = row
    for row in web:
        merged[(row["userId"], row["movieId"])] = row

    payload = list(merged.values())
    stats = {
        "crawled_rows": history_stats["crawled_rows"],
        "web_rows": web_stats["web_rows"],
        "merged_total": len(payload),
    }
    return payload, stats


def export_spark_history_ratings_file(
    output_path: Path | None = None,
    *,
    ensure_seed: bool = True,
) -> int:
    """导出历史爬虫评分 NDJSON（首次部署或历史数据变更时同步到 VM）。"""
    if ensure_seed and CrawledRating.query.count() == 0:
        seed_crawled_ratings()

    output_path = output_path or SPARK_HISTORY_RATINGS
    payload, stats = build_spark_history_payload()
    _write_ndjson_rows(payload, output_path)
    print(
        f"已导出历史评分 {stats['merged_total']} 条 -> {output_path} "
        f"(crawled: {stats['crawled_rows']})"
    )
    return stats["merged_total"]


def export_spark_web_ratings_file(output_path: Path | None = None) -> int:
    """导出网站用户评分 NDJSON（每次刷新推荐时同步）。"""
    output_path = output_path or SPARK_WEB_RATINGS
    payload, stats = build_spark_web_payload()
    _write_ndjson_rows(payload, output_path)
    print(f"已导出网站评分 {stats['merged_total']} 条 -> {output_path}")
    return stats["merged_total"]


def export_spark_ratings_file(output_path: Path | None = None, *, ensure_seed: bool = True) -> int:
    """将数据库评分导出为 Spark NDJSON（全量合并，兼容旧版全量 Spark 任务）。"""
    if ensure_seed and CrawledRating.query.count() == 0:
        seed_crawled_ratings()

    output_path = output_path or SPARK_DATA_DIR / "ratings.json"
    payload, stats = build_spark_ratings_payload()
    _write_ndjson_rows(payload, output_path)
    print(
        f"已导出 {stats['merged_total']} 条评分 -> {output_path} "
        f"(数据库 crawled: {stats['crawled_rows']}, web: {stats['web_rows']})"
    )
    return stats["merged_total"]
