"""从 MySQL 导出电影特征目录，供 Spark TF-IDF 内容推荐（替代 films_data CSV）。"""
from __future__ import annotations

import json
from pathlib import Path

from config import SPARK_DATA_DIR
from services.movie_service import get_mysql


def _feature_text(row: dict) -> str:
    parts = [
        row.get("genres"),
        row.get("directors"),
        row.get("actors"),
        row.get("languages"),
        row.get("countries"),
    ]
    return " ".join(str(part).strip() for part in parts if part and str(part).strip())


def build_movies_catalog_payload() -> list[dict]:
    """从 MySQL movies 表读取 TF-IDF 所需特征。"""
    payload: list[dict] = []
    with get_mysql() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT movie_id, genres, directors, actors, languages, countries
                FROM movies
                WHERE movie_id IS NOT NULL
                """
            )
            for row in cur.fetchall():
                movie_id = row.get("movie_id")
                if movie_id is None:
                    continue
                text = _feature_text(row)
                if not text:
                    continue
                payload.append({"movieId": str(movie_id), "featureText": text})
    return payload


def export_spark_movies_catalog_file(output_path: Path | None = None) -> int:
    """将 MySQL 电影特征导出为 Spark NDJSON（VM 同步用，非持久数据源）。"""
    output_path = output_path or SPARK_DATA_DIR / "movies_catalog.ndjson"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_movies_catalog_payload()
    with output_path.open("w", encoding="utf-8") as handle:
        for row in payload:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"已导出 {len(payload)} 部电影特征 -> {output_path} (来源: MySQL movies)")
    return len(payload)
