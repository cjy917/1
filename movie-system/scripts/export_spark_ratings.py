"""导出评分数据供 Spark ALS / GraphX 使用（films_data 爬虫评分 + Web 用户评分）。"""
import csv
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from config import FILMS_RATINGS_DIR, SPARK_DATA_DIR
from models import UserRating, db


def _string_user_id(name: str) -> int:
    name = (name or "unknown").strip()
    return abs(hash(f"films::{name}")) % (2**31 - 1)


def load_films_data_ratings() -> list[dict]:
    rows: list[dict] = []
    if not FILMS_RATINGS_DIR.exists():
        return rows
    for csv_path in sorted(FILMS_RATINGS_DIR.glob("part-*.csv")):
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                movie_id = str(row.get("movie_id", "")).strip()
                user_name = str(row.get("user_id", "")).strip()
                rating = float(row.get("rating") or 0)
                if movie_id and user_name and rating > 0:
                    rows.append(
                        {
                            "userId": _string_user_id(user_name),
                            "movieId": movie_id,
                            "rating": rating,
                        }
                    )
    return rows


def load_web_ratings() -> list[dict]:
    rows: list[dict] = []
    app = create_app()
    with app.app_context():
        web_user_offset = 1_000_000
        for rating in UserRating.query.all():
            rows.append(
                {
                    "userId": web_user_offset + rating.user_id,
                    "movieId": str(rating.movie_id),
                    "rating": rating.score,
                }
            )
    return rows


def export_ratings(output_path: Path | None = None) -> int:
    output_path = output_path or SPARK_DATA_DIR / "ratings.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    films_rows = load_films_data_ratings()
    web_rows = load_web_ratings()
    merged: dict[tuple[int, str], dict] = {}
    for row in films_rows:
        merged[(row["userId"], row["movieId"])] = row
    for row in web_rows:
        merged[(row["userId"], row["movieId"])] = row

    payload = [
        {"userId": k[0], "movieId": k[1], "rating": v["rating"]}
        for k, v in merged.items()
    ]
    # Spark json 数据源按「每行一个 JSON 对象」解析；根级 JSON 数组会被当成 1 条记录
    with output_path.open("w", encoding="utf-8") as handle:
        for row in payload:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"已导出 {len(payload)} 条评分 -> {output_path}")
    print(f"  films_data: {len(films_rows)} 条, Web 用户: {len(web_rows)} 条")
    return len(payload)


if __name__ == "__main__":
    export_ratings()
