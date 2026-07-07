"""
【详情页 D1】Hero 主题色提取
路由：GET /api/movies/<id>/hero-theme
从海报采样 RGB，供前端 buildHeroFlowStyle / buildHeroScrimStyle
"""
from __future__ import annotations

import os
from typing import Any

from PIL import Image

from services.movie_service import resolve_poster_file

DEFAULT_OVERLAY = (
    "linear-gradient(to right, rgba(3, 37, 65, 0.96) 0%, "
    "rgba(13, 37, 63, 0.88) 42%, rgba(20, 33, 61, 0.72) 100%)"
)

DEFAULT_THEME: dict[str, Any] = {
    "r": 13,
    "g": 37,
    "b": 63,
    "overlay": DEFAULT_OVERLAY,
}

# movie_id → (mtime, theme) 避免重复读盘
_theme_cache: dict[int, tuple[float, dict[str, Any]]] = {}


def _clamp(value: int) -> int:
    return max(0, min(255, value))


def _darken(r: int, g: int, b: int, factor: float) -> tuple[int, int, int]:
    return (
        _clamp(int(r * factor)),
        _clamp(int(g * factor)),
        _clamp(int(b * factor)),
    )


def build_overlay(r: int, g: int, b: int) -> str:
    """CSS linear-gradient 遮罩（后端备用，前端主要用 heroTheme.js）"""
    left = _darken(r, g, b, 0.26)
    mid = _darken(r, g, b, 0.38)
    right = _darken(r, g, b, 0.5)
    return (
        f"linear-gradient(to right, rgba({left[0]}, {left[1]}, {left[2]}, 0.96) 0%, "
        f"rgba({mid[0]}, {mid[1]}, {mid[2]}, 0.86) 42%, "
        f"rgba({right[0]}, {right[1]}, {right[2]}, 0.68) 100%)"
    )


def _extract_theme_from_file(path: str) -> dict[str, Any]:
    """16×16 采样，过滤过暗/过亮/低饱和像素后取平均色"""
    try:
        with Image.open(path) as img:
            sample = img.convert("RGB").resize((16, 16), Image.Resampling.BILINEAR)
            pixels = list(sample.getdata())

        rs = gs = bs = 0
        count = 0
        for r, g, b in pixels:
            max_c = max(r, g, b)
            min_c = min(r, g, b)
            sat = 0 if max_c == 0 else (max_c - min_c) / max_c
            lum = (r * 0.299 + g * 0.587 + b * 0.114) / 255
            if lum < 0.1 or lum > 0.93 or sat < 0.07:
                continue
            rs += r
            gs += g
            bs += b
            count += 1

        if count < 4:
            return dict(DEFAULT_THEME)

        r = round(rs / count)
        g = round(gs / count)
        b = round(bs / count)
        return {"r": r, "g": g, "b": b, "overlay": build_overlay(r, g, b)}
    except Exception:
        return dict(DEFAULT_THEME)


def get_movie_hero_theme(movie_id: int, cover_path: str | None = None) -> dict[str, Any]:
    """入口：按海报 mtime 缓存主题"""
    file_path = resolve_poster_file(movie_id, cover_path)
    if not file_path:
        return dict(DEFAULT_THEME)

    try:
        mtime = os.path.getmtime(file_path)
    except OSError:
        return dict(DEFAULT_THEME)

    cached = _theme_cache.get(movie_id)
    if cached and cached[0] == mtime:
        return cached[1]

    theme = _extract_theme_from_file(file_path)
    _theme_cache[movie_id] = (mtime, theme)
    return theme
