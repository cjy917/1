"""下载首页 Hero + 热门电影栏的 TMDB 预告片到本地 trailers/ 目录。

有网时运行一次即可；之后断网时系统会优先播放本地 MP4，展示与在线一致。

用法:
  pip install yt-dlp imageio-ffmpeg
  python scripts/download_home_trailers.py
  python scripts/download_home_trailers.py --force
  python scripts/download_home_trailers.py --quality 1080
  python scripts/download_home_trailers.py --sections banner,popular

默认：Hero 全部（6 部）+ 热门电影前 6 部，去重后约 12 部。
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from config import TRAILER_DIR  # noqa: E402
from config import POPULAR_TRAILER_DOWNLOAD_SIZE  # noqa: E402
from services.movie_service import get_home_sections, get_home_trailer_targets  # noqa: E402
from services.trailer_service import (  # noqa: E402
    TRAILER_EXTENSIONS,
    _save_trailer_cache,
    get_local_trailer_path,
    resolve_youtube_key_for_movie,
)

MIN_BYTES = 64 * 1024
# 低于此体积多半是 YouTube 360p 单文件（无 ffmpeg 时），应重新下载
LOW_QUALITY_MAX_MB = 8


def log(msg: str) -> None:
    text = str(msg)
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        print(text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8", errors="replace"), flush=True)


def ensure_yt_dlp() -> None:
    try:
        import yt_dlp  # noqa: F401
        return
    except ImportError:
        pass
    log("正在安装 yt-dlp …")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp", "-q"])


def resolve_ffmpeg() -> str | None:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    log("正在安装 imageio-ffmpeg（内置 ffmpeg，用于合并 1080p 视频）…")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "imageio-ffmpeg", "-q"])
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def build_format_selector(max_height: int, has_ffmpeg: bool) -> str:
    if has_ffmpeg:
        return (
            f"bestvideo[height<={max_height}][vcodec^=avc1]+bestaudio[ext=m4a]/"
            f"bestvideo[height<={max_height}]+bestaudio/"
            f"best[height<={max_height}]"
        )
    log("  警告：未找到 ffmpeg，只能下载约 360p 单文件，画质会偏糊")
    return f"best[height<={max_height}][ext=mp4]/best[height<={max_height}]/best"


def is_low_quality_file(path: Path) -> bool:
    return path.stat().st_size < LOW_QUALITY_MAX_MB * 1024 * 1024


def collect_movies(sections: list[str]) -> list[dict]:
    if sections == ["banner", "popular"]:
        return get_home_trailer_targets()
    data = get_home_sections()
    seen: set[int] = set()
    movies: list[dict] = []
    for key in sections:
        items = data.get(key, [])
        if key == "popular":
            items = items[:POPULAR_TRAILER_DOWNLOAD_SIZE]
        for movie in items:
            movie_id = int(movie["movie_id"])
            if movie_id in seen:
                continue
            seen.add(movie_id)
            movies.append(movie)
    return movies


def cleanup_partial(movie_id: int) -> None:
    for path in TRAILER_DIR.glob(f"{movie_id}.*"):
        if path.suffix.lower() not in TRAILER_EXTENSIONS:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        elif path.stat().st_size < MIN_BYTES:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def normalize_output(movie_id: int) -> Path | None:
    target = TRAILER_DIR / f"{movie_id}.mp4"
    if target.exists() and target.stat().st_size >= MIN_BYTES:
        return target
    candidates = [
        p for p in TRAILER_DIR.glob(f"{movie_id}.*")
        if p.suffix.lower() in TRAILER_EXTENSIONS and p.stat().st_size >= MIN_BYTES
    ]
    if not candidates:
        return None
    source = max(candidates, key=lambda p: p.stat().st_size)
    if source != target:
        if target.exists():
            target.unlink()
        shutil.move(str(source), str(target))
    for extra in TRAILER_DIR.glob(f"{movie_id}.*"):
        if extra != target:
            extra.unlink(missing_ok=True)
    return target


def download_youtube_trailer(movie_id: int, youtube_key: str, max_height: int = 1080) -> Path | None:
    import yt_dlp

    ffmpeg = resolve_ffmpeg()
    TRAILER_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_partial(movie_id)
    temp_base = TRAILER_DIR / f"{movie_id}"
    url = f"https://www.youtube.com/watch?v={youtube_key}"
    ydl_opts = {
        "format": build_format_selector(max_height, bool(ffmpeg)),
        "merge_output_format": "mp4",
        "outtmpl": str(temp_base) + ".%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "retries": 10,
        "fragment_retries": 10,
        "file_access_retries": 5,
        "socket_timeout": 60,
        "overwrites": True,
        "nocheckcertificate": True,
        "postprocessor_args": {"ffmpeg": ["-c:v", "copy", "-c:a", "aac", "-movflags", "+faststart"]},
    }
    if ffmpeg:
        ydl_opts["ffmpeg_location"] = ffmpeg
    ydl_opts["proxy"] = ""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:
        log(f"  yt-dlp 失败: {exc}")
        cleanup_partial(movie_id)
        return None
    return normalize_output(movie_id)


def update_playback_cache(app, movie_id: int, tmdb_id: str | None) -> None:
    with app.app_context():
        _save_trailer_cache(movie_id, "mp4", f"local:{movie_id}", tmdb_id)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="下载首页展示电影的本地预告片")
    parser.add_argument(
        "--sections",
        default="banner,popular",
        help="逗号分隔：banner,popular,top_rated,latest",
    )
    parser.add_argument("--force", action="store_true", help="已存在时也重新下载")
    parser.add_argument(
        "--quality",
        type=int,
        default=1080,
        choices=(480, 720, 1080),
        help="最高视频高度，默认 1080",
    )
    args = parser.parse_args()
    sections = [s.strip() for s in args.sections.split(",") if s.strip()]

    ensure_yt_dlp()
    ffmpeg = resolve_ffmpeg()
    if ffmpeg:
        log(f"ffmpeg: {ffmpeg}")
    log(f"目标清晰度: 最高 {args.quality}p\n")
    movies = collect_movies(sections)
    if not movies:
        raise SystemExit("未找到需要下载的电影")

    from app import create_app

    app = create_app()
    TRAILER_DIR.mkdir(parents=True, exist_ok=True)

    ok, skip, fail = 0, 0, 0
    log(f"共 {len(movies)} 部电影（{', '.join(sections)}）\n")

    for index, movie in enumerate(movies, 1):
        movie_id = int(movie["movie_id"])
        title = movie.get("title") or movie_id
        prefix = f"[{index}/{len(movies)}] {title}"

        existing = get_local_trailer_path(movie_id)
        if existing and not args.force:
            if is_low_quality_file(existing):
                log(f"{prefix} — 检测到旧版低清文件 ({existing.stat().st_size / 1024 / 1024:.1f} MB)，重新下载 …")
            else:
                log(f"{prefix} — 已有本地预告，跳过")
                update_playback_cache(app, movie_id, None)
                skip += 1
                continue

        log(f"{prefix} — 解析 TMDB 预告 …")
        youtube_key, tmdb_id = resolve_youtube_key_for_movie(movie)
        if not youtube_key:
            log(f"{prefix} — 未找到 YouTube 预告")
            fail += 1
            continue

        log(f"{prefix} — 下载 {youtube_key} …")
        path = download_youtube_trailer(movie_id, youtube_key, args.quality)
        if not path:
            log(f"{prefix} — 下载失败")
            fail += 1
            continue

        update_playback_cache(app, movie_id, tmdb_id)
        size_mb = path.stat().st_size / (1024 * 1024)
        log(f"{prefix} — 完成 ({size_mb:.1f} MB) -> {path.name}")
        ok += 1
        time.sleep(0.3)

    log(f"\n完成：成功 {ok}，跳过 {skip}，失败 {fail}")
    log(f"预告片目录：{TRAILER_DIR}")


if __name__ == "__main__":
    main()
