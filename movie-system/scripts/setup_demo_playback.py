"""为首页轮播电影下载可播放的本地预告/正片（国内网络可用）。

用法:
  python scripts/setup_demo_playback.py --limit 20
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent.parent
BACKEND_DIR = BASE_DIR.parent / "backend"
VIDEO_DIR = ROOT_DIR / "videos"
TRAILER_DIR = ROOT_DIR / "trailers"
ASSETS_DIR = ROOT_DIR / "movie-system" / "media"

DEMO_MP4 = "https://www.w3school.com.cn/example/html5/mov_bbb.mp4"

sys.path.insert(0, str(BACKEND_DIR))
from services.movie_service import get_home_sections  # noqa: E402


def download_file(url: str, target: Path) -> bool:
    if target.exists() and target.stat().st_size > 1024:
        return True
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with requests.get(url, stream=True, timeout=60, headers={"User-Agent": "FYWZ-Movies/1.0"}) as resp:
            resp.raise_for_status()
            with target.open("wb") as handle:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        handle.write(chunk)
        return target.stat().st_size > 1024
    except Exception as exc:
        print(f"  下载失败: {exc}")
        return False


def main(limit: int) -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    asset = ASSETS_DIR / "demo.mp4"
    if not download_file(DEMO_MP4, asset):
        raise SystemExit("无法下载演示 MP4，请检查网络")

    sections = get_home_sections()
    movies = sections.get("banner", [])[:limit]
    if not movies:
        raise SystemExit("未找到轮播电影")

    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    TRAILER_DIR.mkdir(parents=True, exist_ok=True)

    for movie in movies:
        mid = movie["movie_id"]
        video_path = VIDEO_DIR / f"{mid}.mp4"
        trailer_path = TRAILER_DIR / f"{mid}.mp4"
        shutil.copy2(asset, video_path)
        shutil.copy2(asset, trailer_path)
        print(f"[OK] {movie['title']} -> videos/{mid}.mp4, trailers/{mid}.mp4")
        time.sleep(0.05)

    print(f"完成：已为 {len(movies)} 部电影配置本地可播放文件")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    main(args.limit)
