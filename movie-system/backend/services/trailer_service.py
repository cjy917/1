import re
from pathlib import Path
from urllib.parse import quote

from services.http_client import external_get

from config import TMDB_API_KEY, TRAILER_DIR
from models import PlaybackCache, db
from services.tmdb_meta import extract_english_title, extract_tmdb_id, fetch_tmdb_backdrop_url, resolve_tmdb_id

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
}

YOUTUBE_KEY_RE = re.compile(r"[A-Za-z0-9_-]{11}")
TRAILER_EXTENSIONS = (".mp4", ".webm", ".m4v")
REQUEST_TIMEOUT = 12
YOUTUBE_SEARCH_TIMEOUT = 3

_trailer_memory_cache: dict[int, dict] = {}


TRAILER_LABEL = "TMDB 官方预告"


def build_youtube_embed(key: str, autoplay: bool = False) -> str:
    params = "rel=0&modestbranding=1&playsinline=1&iv_load_policy=3&disablekb=1&fs=0&cc_load_policy=0"
    if autoplay:
        params += f"&autoplay=1&mute=1&loop=1&playlist={key}&controls=0"
    return f"https://www.youtube-nocookie.com/embed/{key}?{params}"


def get_local_trailer_path(movie_id: str | int) -> Path | None:
    TRAILER_DIR.mkdir(parents=True, exist_ok=True)
    for ext in TRAILER_EXTENSIONS:
        candidate = TRAILER_DIR / f"{movie_id}{ext}"
        if candidate.exists() and candidate.stat().st_size > 1024:
            return candidate
    return None


def list_local_trailer_ids() -> list[int]:
    TRAILER_DIR.mkdir(parents=True, exist_ok=True)
    ids: list[int] = []
    for ext in TRAILER_EXTENSIONS:
        for path in TRAILER_DIR.glob(f"*{ext}"):
            if path.stat().st_size <= 1024:
                continue
            try:
                ids.append(int(path.stem))
            except ValueError:
                continue
    return sorted(set(ids))


def _pick_best_youtube_key(items: list[dict]) -> str | None:
    priority = {"Trailer": 0, "Teaser": 1, "Clip": 2}
    candidates: list[tuple[int, str]] = []
    for item in items:
        if item.get("site") != "YouTube":
            continue
        key = item.get("key") or ""
        if not YOUTUBE_KEY_RE.fullmatch(key):
            continue
        rank = priority.get(item.get("type") or "Clip", 9)
        if item.get("official"):
            rank -= 0.5
        candidates.append((rank, key))
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def _fetch_tmdb_trailer_key(tmdb_id: str) -> str | None:
    if not TMDB_API_KEY or not tmdb_id:
        return None
    try:
        response = external_get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos",
            params={"api_key": TMDB_API_KEY, "language": "en-US"},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        key = _pick_best_youtube_key(response.json().get("results", []))
        if key:
            return key
        response = external_get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}/videos",
            params={"api_key": TMDB_API_KEY, "language": "zh-CN"},
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return _pick_best_youtube_key(response.json().get("results", []))
    except Exception:
        return None


def _fetch_youtube_search(title: str) -> str | None:
    """TMDB 无预告时的兜底；短超时，避免拖慢详情页。"""
    try:
        url = f"https://www.youtube.com/results?search_query={quote(title + ' official trailer')}"
        response = external_get(url, headers=HEADERS, timeout=YOUTUBE_SEARCH_TIMEOUT)
        response.raise_for_status()
        keys = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', response.text)
        return keys[0] if keys else None
    except Exception:
        return None


def _payload(
    trailer_type: str,
    video_key: str,
    embed_url: str,
    watch_url: str | None = None,
    message: str | None = None,
    tmdb_id: str | None = None,
) -> dict:
    data = {
        "type": trailer_type,
        "video_key": video_key,
        "embed_url": embed_url,
        "watch_url": watch_url or embed_url,
        "message": message,
    }
    if tmdb_id:
        data["tmdb_id"] = tmdb_id
    return data


def _enrich_backdrop(data: dict, tmdb_id: str | None = None) -> dict:
    tid = tmdb_id or data.get("tmdb_id")
    if not tid or data.get("backdrop_url"):
        return data
    backdrop_url = fetch_tmdb_backdrop_url(str(tid))
    if not backdrop_url:
        return data
    enriched = {**data, "backdrop_url": backdrop_url}
    if not enriched.get("tmdb_id"):
        enriched["tmdb_id"] = str(tid)
    return enriched


def _maybe_enrich_backdrop(data: dict, tmdb_id: str | None, autoplay: bool) -> dict:
    if not autoplay:
        return data
    return _enrich_backdrop(data, tmdb_id)


def _none_payload(message: str = "暂无官方预告片") -> dict:
    return {
        "type": "none",
        "video_key": None,
        "embed_url": None,
        "watch_url": None,
        "message": message,
    }


def _save_trailer_cache(movie_id: int, trailer_type: str, video_key: str, tmdb_id: str | None = None) -> None:
    cache = db.session.get(PlaybackCache, movie_id)
    if not cache:
        cache = PlaybackCache(movie_id=movie_id)
        db.session.add(cache)
    cache.trailer_type = trailer_type
    cache.trailer_key = video_key
    if tmdb_id:
        cache.tmdb_id = tmdb_id
    db.session.commit()


def _load_trailer_cache(movie_id: int) -> dict | None:
    cache = db.session.get(PlaybackCache, movie_id)
    if not cache or not cache.trailer_key or not cache.trailer_type:
        return None
    if cache.trailer_type == "none" or cache.trailer_key == "demo":
        return None
    key = cache.trailer_key
    t = cache.trailer_type
    if t == "youtube":
        return _payload(
            "youtube",
            key,
            build_youtube_embed(key),
            f"https://www.youtube.com/watch?v={key}",
            "TMDB 官方预告",
            cache.tmdb_id,
        )
    if t == "mp4":
        return _payload("mp4", key, f"/api/trailers/{movie_id}", f"/api/trailers/{movie_id}", TRAILER_LABEL)
    return None


def _local_trailer_payload(movie_id: int, tmdb_id: str | None = None) -> dict:
    data = _payload(
        "mp4",
        f"local:{movie_id}",
        f"/api/trailers/{movie_id}",
        f"/api/trailers/{movie_id}",
        TRAILER_LABEL,
        tmdb_id,
    )
    _trailer_memory_cache[movie_id] = data
    return data


def resolve_trailer(movie: dict, autoplay: bool = False) -> dict:
    movie_id = int(movie["movie_id"])
    title = movie.get("title") or ""
    aliases = movie.get("aliases") or ""
    release_year = movie.get("release_year")
    detail_url = movie.get("detail_url")

    local_path = get_local_trailer_path(movie_id)
    if local_path:
        tmdb_id = extract_tmdb_id(movie_id, detail_url)
        if not detail_url or tmdb_id == str(movie_id):
            try:
                cached = _load_trailer_cache(movie_id)
                if cached and cached.get("tmdb_id"):
                    tmdb_id = cached["tmdb_id"]
                else:
                    db_cache = db.session.get(PlaybackCache, movie_id)
                    if db_cache and db_cache.tmdb_id:
                        tmdb_id = db_cache.tmdb_id
            except Exception:
                pass
        result = _local_trailer_payload(movie_id, tmdb_id if tmdb_id != str(movie_id) else None)
        try:
            _save_trailer_cache(movie_id, "mp4", f"local:{movie_id}", result.get("tmdb_id"))
        except Exception:
            pass
        return result

    tmdb_id = resolve_tmdb_id(
        movie_id,
        title=title,
        aliases=aliases,
        release_year=release_year,
        detail_url=detail_url,
    )

    if movie_id in _trailer_memory_cache:
        cached = _trailer_memory_cache[movie_id]
        if cached["type"] == "youtube" and autoplay:
            cached = {**cached, "embed_url": build_youtube_embed(cached["video_key"], True)}
        return _maybe_enrich_backdrop(cached, cached.get("tmdb_id"), autoplay)

    cached = _load_trailer_cache(movie_id)
    if cached:
        if cached["type"] == "youtube":
            cached["embed_url"] = build_youtube_embed(cached["video_key"], autoplay)
        cached = _maybe_enrich_backdrop(cached, cached.get("tmdb_id"), autoplay)
        _trailer_memory_cache[movie_id] = cached
        return cached

    youtube_key = _fetch_tmdb_trailer_key(tmdb_id) if tmdb_id else None
    if not youtube_key:
        search_title = extract_english_title(title, aliases) or title
        if search_title:
            youtube_key = _fetch_youtube_search(f"{search_title} official trailer")

    if youtube_key:
        result = _maybe_enrich_backdrop(
            _payload(
                "youtube",
                youtube_key,
                build_youtube_embed(youtube_key, autoplay),
                f"https://www.youtube.com/watch?v={youtube_key}",
                "TMDB 官方预告",
                tmdb_id,
            ),
            tmdb_id,
            autoplay,
        )
        _save_trailer_cache(movie_id, "youtube", youtube_key, tmdb_id)
        _trailer_memory_cache[movie_id] = result
        return result

    result = _maybe_enrich_backdrop(_none_payload(), tmdb_id, autoplay)
    _save_trailer_cache(movie_id, "none", "none")
    _trailer_memory_cache[movie_id] = result
    return result


def resolve_youtube_key_for_movie(movie: dict) -> tuple[str | None, str | None]:
    """解析电影对应的 YouTube 预告 key，供离线下载脚本使用。"""
    movie_id = int(movie["movie_id"])
    title = movie.get("title") or ""
    aliases = movie.get("aliases") or ""
    release_year = movie.get("release_year")
    tmdb_id = resolve_tmdb_id(
        movie_id,
        title=title,
        aliases=aliases,
        release_year=release_year,
        detail_url=movie.get("detail_url"),
    )
    youtube_key = _fetch_tmdb_trailer_key(tmdb_id) if tmdb_id else None
    search_title = extract_english_title(title, aliases) or title
    if not youtube_key and search_title:
        youtube_key = _fetch_youtube_search(f"{search_title} official trailer")
    return youtube_key, tmdb_id
