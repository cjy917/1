"""修复数据库中缺失的海报路径（豆瓣 p*.webp + TMDB id_*.jpg）。"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from config import DATA_DIR, POSTER_DIR
from models import Movie, db


def resolve_poster(movie_id: str, cover_path: str = "") -> str | None:
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


def load_cover_paths() -> dict[str, str]:
    mapping: dict[str, str] = {}
    cleaned = DATA_DIR / "cleaned_data"
    if not cleaned.exists():
        return mapping
    for csv_path in cleaned.rglob("part-*.csv"):
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                mid = str(row.get("movie_id", "")).strip()
                cover = (row.get("cover_path") or "").strip()
                if mid and cover:
                    mapping[mid] = cover
    return mapping


def fix_posters() -> None:
    app = create_app()
    cover_map = load_cover_paths()

    with app.app_context():
        fixed = 0
        missing = 0
        for movie in Movie.query.all():
            cover = cover_map.get(movie.movie_id, "")
            path = resolve_poster(movie.movie_id, cover)
            if path:
                if movie.poster_path != path:
                    movie.poster_path = path
                    fixed += 1
            else:
                missing += 1
        db.session.commit()
        with_poster = Movie.query.filter(Movie.poster_path.isnot(None)).count()
        total = Movie.query.count()
        print(f"更新海报路径: {fixed} 条")
        print(f"当前有封面: {with_poster}/{total}，仍缺失: {missing}")


if __name__ == "__main__":
    fix_posters()
