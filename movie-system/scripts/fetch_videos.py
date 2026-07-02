"""为电影补充正片视频地址（Internet Archive 公版电影，需在可访问 IA 的网络环境运行）。"""
import argparse
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from models import Movie, db
from services.archive_service import fetch_archive_video_url
from services.video_service import get_local_video_path


def link_archive_videos(limit: int = 20, sleep_seconds: float = 1.0) -> None:
    app = create_app()
    with app.app_context():
        movies = (
            Movie.query.filter((Movie.video_url.is_(None)) | (Movie.video_url == ""))
            .order_by(Movie.rating.desc())
            .limit(limit)
            .all()
        )
        updated = 0
        for movie in movies:
            if get_local_video_path(movie.movie_id):
                continue
            url = fetch_archive_video_url(movie.title, movie.aliases or "")
            if url:
                movie.video_url = url
                updated += 1
                print(f"[OK] {movie.title} -> {url}")
            else:
                print(f"[SKIP] {movie.title}")
            time.sleep(sleep_seconds)
        db.session.commit()
        print(f"Done. Linked {updated}/{len(movies)} movies.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    link_archive_videos(limit=args.limit)
