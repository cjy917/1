"""从 CSV 的「视频地址」列更新数据库，无需重新全量导入。"""
import csv
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
ROOT_DIR = BACKEND_DIR.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from config import DATA_DIR
from models import Movie, db


def main() -> None:
    csv_path = DATA_DIR / "movies.csv"
    app = create_app()
    updated = 0
    with app.app_context():
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                movie_id = str(row.get("电影ID", "")).strip()
                video_url = (row.get("视频地址") or row.get("video_url") or "").strip()
                if not movie_id or not video_url:
                    continue
                movie = Movie.query.filter_by(movie_id=movie_id).first()
                if movie and movie.video_url != video_url:
                    movie.video_url = video_url
                    updated += 1
        db.session.commit()
    print(f"Updated {updated} video URLs from CSV.")


if __name__ == "__main__":
    main()
