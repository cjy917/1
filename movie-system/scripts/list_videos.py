"""扫描本地 videos 目录，列出已有正片的电影。"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
VIDEO_DIR = BACKEND_DIR.parent.parent / "merged" / "videos"
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from models import Movie
from services.video_service import get_local_video_path


def main() -> None:
    app = create_app()
    with app.app_context():
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)
        local_files = sorted(VIDEO_DIR.glob("*.*"))
        print(f"本地视频目录: {VIDEO_DIR}")
        print(f"文件数量: {len(local_files)}")
        for path in local_files:
            movie_id = path.stem
            movie = Movie.query.filter_by(movie_id=movie_id).first()
            title = movie.title if movie else "未知"
            size_mb = path.stat().st_size / 1024 / 1024
            print(f"  {movie_id} | {title} | {size_mb:.1f} MB")

        playable = Movie.query.count()
        with_local = sum(1 for movie in Movie.query.all() if get_local_video_path(movie.movie_id))
        with_url = Movie.query.filter(Movie.video_url.isnot(None), Movie.video_url != "").count()
        print(f"\n数据库电影: {playable}")
        print(f"可本地播放: {with_local}")
        print(f"有在线地址: {with_url}")


if __name__ == "__main__":
    main()
