"""从 films_data 清洗数据导入 SQLite，并关联 posters 封面。"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from config import DATA_DIR, POSTER_DIR
from models import Movie, db


def parse_int(value, default=None):
    if value in (None, ""):
        return default
    try:
        return int(float(str(value).replace("分钟", "").strip()))
    except (TypeError, ValueError):
        return default


def parse_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def find_poster(movie_id: str, cover_path: str = "") -> Optional[str]:
    movie_id = str(movie_id).strip()
    if not POSTER_DIR.exists():
        return None
    for pattern in (f"{movie_id}_*", f"{movie_id}.*"):
        matches = sorted(POSTER_DIR.glob(pattern))
        if matches:
            return str(matches[0])
    if cover_path:
        fname = Path(cover_path.replace("\\", "/")).name
        direct = POSTER_DIR / fname
        if direct.exists():
            return str(direct)
        stem = fname.rsplit(".", 1)[0]
        matches = sorted(POSTER_DIR.glob(f"{stem}*"))
        if matches:
            return str(matches[0])
    return None


def iter_movie_csv_files():
    cleaned = DATA_DIR / "cleaned_data"
    files: list[Path] = []
    if not cleaned.exists():
        return files
    for csv_dir in cleaned.rglob("*_cleaned.csv"):
        if csv_dir.is_dir():
            files.extend(sorted(csv_dir.glob("part-*.csv")))
    return files


def import_films_data(force: bool = False) -> int:
    app = create_app()
    csv_files = iter_movie_csv_files()
    if not csv_files:
        raise SystemExit(f"未找到 films_data CSV，请确认目录: {DATA_DIR / 'cleaned_data'}")

    with app.app_context():
        db.create_all()
        if Movie.query.count() > 0 and not force:
            print(f"数据库已有 {Movie.query.count()} 部电影，跳过导入。使用 --force 强制重新导入。")
            return Movie.query.count()

        if force:
            Movie.query.delete()
            db.session.commit()

        seen_ids: set[str] = set()
        count = 0
        for csv_path in csv_files:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    movie_id = str(row.get("movie_id", "")).strip()
                    if not movie_id or movie_id in seen_ids:
                        continue
                    seen_ids.add(movie_id)

                    genres = (row.get("genres") or "").replace("|", ",")
                    poster = find_poster(movie_id, row.get("cover_path") or "")
                    movie = Movie(
                        movie_id=movie_id,
                        title=(row.get("title") or "").strip(),
                        rating=parse_float(row.get("rating")),
                        rating_count=parse_int(row.get("rating_count"), 0),
                        release_date=(row.get("release_date") or "").strip(),
                        release_year=parse_int(row.get("release_year")),
                        director=(row.get("directors") or "").replace("|", ","),
                        writer=(row.get("writers") or "").replace("|", ","),
                        actors=(row.get("actors") or "").replace("|", ","),
                        aliases=(row.get("aliases") or "").replace("|", ","),
                        summary=(row.get("summary") or "").strip(),
                        detail_url=(row.get("detail_url") or "").strip(),
                        language=(row.get("languages") or "").replace("|", ","),
                        genres=genres,
                        duration=parse_int(row.get("duration")),
                        crawled_reviews=(row.get("reviews") or "").strip(),
                        country=(row.get("countries") or "").replace("|", ","),
                        awards=(row.get("awards") or "").strip(),
                        review_count=parse_int(row.get("review_count"), 0),
                        poster_path=poster,
                    )
                    db.session.add(movie)
                    count += 1
                    if count % 500 == 0:
                        db.session.commit()
                        print(f"已导入 {count} 部电影...")
        db.session.commit()
    return count


if __name__ == "__main__":
    force_import = "--force" in sys.argv
    total = import_films_data(force=force_import)
    print(f"导入完成: {total} 部电影")
