"""下载电影正片到本地 videos 目录，供网页直接播放。"""
import argparse
import sys
from pathlib import Path

import requests

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
ROOT_DIR = BACKEND_DIR.parent.parent
VIDEO_DIR = ROOT_DIR / "merged" / "videos"
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from models import Movie, db


def download_video(url: str, target: Path, chunk_size: int = 1024 * 1024) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    handle.write(chunk)


def main() -> None:
    parser = argparse.ArgumentParser(description="下载电影正片 MP4")
    parser.add_argument("--movie-id", required=True, help="电影 ID")
    parser.add_argument("--url", help="视频直链；不传则使用数据库中的 video_url")
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        movie = Movie.query.filter_by(movie_id=str(args.movie_id)).first()
        if not movie:
            raise SystemExit(f"未找到电影 ID: {args.movie_id}")

        url = (args.url or movie.video_url or "").strip()
        if not url:
            raise SystemExit("没有可用视频地址。请传 --url 或在数据库/CSV 中填写 video_url")

        target = VIDEO_DIR / f"{args.movie_id}.mp4"
        print(f"Downloading {movie.title} -> {target}")
        download_video(url, target)
        movie.video_url = url
        db.session.commit()
        print(f"Done. 文件大小: {target.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
