"""海报缩略图：磁盘缓存 + WebP，供列表/马赛克等小图场景。"""
from __future__ import annotations

import os
from pathlib import Path

from flask import Response, send_file
from PIL import Image

from config import POSTER_THUMB_DIR
from services.movie_service import resolve_poster_file

THUMB_MAX_WIDTH = 480
THUMB_MIN_WIDTH = 64
THUMB_QUALITY = 78


def _clamp_width(width: int) -> int:
    return max(THUMB_MIN_WIDTH, min(THUMB_MAX_WIDTH, width))


def _thumb_path(movie_id: int, width: int) -> Path:
    return POSTER_THUMB_DIR / f"{movie_id}_w{width}.webp"


def try_send_poster_thumb(
    movie_id: int,
    cover_path: str | None,
    width: int,
) -> Response | None:
    """生成或读取缓存缩略图；无本地海报时返回 None。"""
    source = resolve_poster_file(movie_id, cover_path)
    if not source:
        return None

    width = _clamp_width(width)
    dest = _thumb_path(movie_id, width)

    try:
        source_mtime = os.path.getmtime(source)
    except OSError:
        return None

    if not dest.exists() or dest.stat().st_mtime < source_mtime:
        try:
            POSTER_THUMB_DIR.mkdir(parents=True, exist_ok=True)
            with Image.open(source) as img:
                rgba = img.convert("RGBA")
                src_w, src_h = rgba.size
                if src_w <= 0 or src_h <= 0:
                    return None
                new_w = min(width, src_w)
                new_h = max(1, int(src_h * new_w / src_w))
                resized = rgba.resize((new_w, new_h), Image.Resampling.BILINEAR)
                resized.save(dest, "WEBP", quality=THUMB_QUALITY, method=4)
        except Exception:
            if dest.exists():
                try:
                    dest.unlink()
                except OSError:
                    pass
            return None

    response = send_file(dest, mimetype="image/webp")
    response.headers["Cache-Control"] = "public, max-age=604800, immutable"
    return response
