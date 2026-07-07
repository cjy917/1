"""
【详情页 D1d】正片播放解析
路由：GET /api/movies/<id>/play、GET /api/videos/<id>
优先级：本地 videos/ 文件 → SQLite PlaybackCache → Archive.org 搜索
"""
from pathlib import Path

import requests
from flask import Response, stream_with_context

from config import LOCAL_VIDEO_FILES, VIDEO_DIR
from models import PlaybackCache, db

VIDEO_EXTENSIONS = (".mp4", ".webm", ".mkv", ".m4v")


def _local_candidates(movie_id: str, quality: str = "auto") -> list[Path]:
    """按 quality 与命名规则在 VIDEO_DIR 查找本地正片"""
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path | None) -> None:
        if not path or path in seen:
            return
        if path.exists() and path.stat().st_size > 1024:
            seen.add(path)
            paths.append(path)

    override = LOCAL_VIDEO_FILES.get(int(movie_id)) if movie_id.isdigit() else None
    if override:
        add(VIDEO_DIR / override)

    quality_map = {
        "720": [f"{movie_id}_720", f"{movie_id}"],
        "1080": [f"{movie_id}_1080", f"{movie_id}"],
        "auto": [f"{movie_id}_1080", f"{movie_id}", f"{movie_id}_720"],
    }
    names = quality_map.get(quality, quality_map["auto"])
    for name in names:
        for ext in VIDEO_EXTENSIONS:
            add(VIDEO_DIR / f"{name}{ext}")

    return paths


def get_local_video_path(movie_id: str, quality: str = "auto") -> Path | None:
    candidates = _local_candidates(str(movie_id), quality)
    return candidates[0] if candidates else None


def _get_cached_video_url(movie_id: int) -> str | None:
    """上次解析成功的远程 URL（存 SQLite）"""
    cache = db.session.get(PlaybackCache, movie_id)
    return cache.video_url if cache and cache.video_url else None


def _save_video_url(movie_id: int, url: str, source: str = "remote") -> None:
    cache = db.session.get(PlaybackCache, movie_id)
    if not cache:
        cache = PlaybackCache(movie_id=movie_id)
        db.session.add(cache)
    cache.video_url = url
    cache.video_source = source
    db.session.commit()


def resolve_playback(movie: dict, quality: str = "auto", search_archive: bool = True) -> dict:
    """
    返回前端 MediaPlayer 可用的播放源：
    { type: 'mp4'|'none', stream_url, source, qualities, message }
    """
    movie_id = int(movie["movie_id"])
    title = movie.get("title") or ""

    # 1. 本地文件
    local_path = get_local_video_path(str(movie_id), quality)
    if local_path:
        qualities = []
        if get_local_video_path(str(movie_id), "720"):
            qualities.append("720")
        if get_local_video_path(str(movie_id), "1080"):
            qualities.append("1080")
        return {
            "type": "mp4",
            "stream_url": f"/api/videos/{movie_id}?quality={quality}",
            "title": title,
            "source": "local",
            "qualities": qualities or ["auto"],
            "message": "正在播放正片",
        }

    # 2. 已缓存远程 URL
    remote = _get_cached_video_url(movie_id)
    if remote:
        return {
            "type": "mp4",
            "stream_url": f"/api/videos/{movie_id}?quality={quality}",
            "title": title,
            "source": "archive" if "archive.org" in remote else "remote",
            "qualities": ["auto"],
            "message": "正在播放在线正片",
        }

    # 3. Archive.org 搜索并缓存
    if search_archive:
        from services.archive_service import fetch_archive_video_url

        archive_url = fetch_archive_video_url(title, movie.get("aliases") or "")
        if archive_url:
            _save_video_url(movie_id, archive_url, "archive")
            return {
                "type": "mp4",
                "stream_url": f"/api/videos/{movie_id}?quality={quality}",
                "title": title,
                "source": "archive",
                "qualities": ["auto"],
                "message": "正在播放公版正片",
            }

    return {
        "type": "none",
        "stream_url": None,
        "title": title,
        "source": "none",
        "qualities": [],
        "message": "",
    }


def pick_remote_url(movie_id: int) -> str | None:
    return _get_cached_video_url(movie_id)


def proxy_video_stream(url: str, range_header: str | None = None) -> Response:
    """Range 代理远程 mp4，支持拖动进度条"""
    headers = {"User-Agent": "FYWZ-Movies/1.0"}
    if range_header:
        headers["Range"] = range_header

    upstream = requests.get(url, headers=headers, stream=True, timeout=60)
    upstream.raise_for_status()

    response_headers = {}
    for key in ("Content-Type", "Content-Length", "Content-Range", "Accept-Ranges"):
        if key in upstream.headers:
            response_headers[key] = upstream.headers[key]
    if "Content-Type" not in response_headers:
        response_headers["Content-Type"] = "video/mp4"

    status = upstream.status_code if upstream.status_code in (200, 206) else 200

    def generate():
        try:
            for chunk in upstream.iter_content(chunk_size=1024 * 256):
                if chunk:
                    yield chunk
        finally:
            upstream.close()

    return Response(stream_with_context(generate()), status=status, headers=response_headers)
