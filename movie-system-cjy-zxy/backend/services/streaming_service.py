from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import quote

import requests

from services.tmdb_meta import extract_english_title, resolve_tmdb_id

DOUBAN_ID_RE = re.compile(r"douban\.com/subject/(\d+)")
TMDB_URL_RE = re.compile(r"themoviedb\.org", re.I)
YEAR_RE = re.compile(r"(20\d{2}|19\d{2})")
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]+")
ENGLISH_TAIL_RE = re.compile(r"\s+[A-Za-z][A-Za-z0-9\s':\-,\.!&]*$")
CHINESE_LANGUAGE_MARKERS = (
    "汉语",
    "普通话",
    "国语",
    "中文",
    "粤语",
    "华语",
    "闽南",
    "mandarin",
    "cantonese",
    "chinese",
)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}

# 已知可直接跳转的正片页（movie_id -> url），可按需补充
DIRECT_STREAMING_URLS: dict[int, str] = {
    26794435: "https://v.qq.com/x/cover/zr5a67l333ehzu9/d0032x85stp.html",
}

PLATFORM_META: list[tuple[str, str]] = [
    ("tencent", "腾讯视频"),
    ("iqiyi", "爱奇艺"),
    ("youku", "优酷"),
    ("bilibili", "哔哩哔哩"),
    ("mgtv", "芒果TV"),
]

PLATFORM_LABELS = dict(PLATFORM_META)

FALLBACK_SEARCH_URLS: dict[str, str] = {
    "tencent": "https://v.qq.com/x/search/?q={query}",
    "iqiyi": "https://so.iqiyi.com/so/q_{query}",
    "youku": "https://www.youku.com/ku/websearch?keyword={query}",
    "bilibili": "https://search.bilibili.com/all?keyword={query}",
    "mgtv": "https://so.mgtv.com/so?k={query}",
}

_watch_cache: dict[int, dict[str, Any]] = {}
_WATCH_CACHE_VERSION = 6


def _normalize_title(value: str) -> str:
    text = (value or "").strip().lower()
    for ch in " ·:：|-—_《》「」[]()（）":
        text = text.replace(ch, "")
    return re.sub(r"\s+", "", text)


def _chinese_only(value: str) -> str:
    parts = CHINESE_RE.findall(value or "")
    return "".join(parts)


def _english_only(value: str) -> str:
    chunks = re.findall(r"[A-Za-z][A-Za-z0-9\s':\-,\.!&]{1,}", value or "")
    return " ".join(chunk.strip(" .,-") for chunk in chunks if len(chunk.strip(" .,-")) >= 2)


def _primary_title(title: str, aliases: str = "") -> str:
    for raw in [title, *(aliases or "").split("|")]:
        raw = (raw or "").strip()
        if not raw:
            continue
        chinese = _chinese_only(raw)
        if len(chinese) >= 2:
            return chinese
        cleaned = ENGLISH_TAIL_RE.sub("", raw).strip()
        if cleaned:
            return cleaned
    return (title or "").strip()


def _title_variants(title: str, aliases: str = "") -> list[str]:
    variants: list[str] = []
    seen: set[str] = set()
    for raw in [title, *(aliases or "").split("|")]:
        raw = (raw or "").strip()
        if not raw:
            continue
        for candidate in (
            _normalize_title(raw),
            _normalize_title(_chinese_only(raw)),
            re.sub(r"\s+", "", _english_only(raw).lower()),
            _normalize_title(ENGLISH_TAIL_RE.sub("", raw).strip()),
        ):
            if candidate and candidate not in seen:
                seen.add(candidate)
                variants.append(candidate)
    return variants


def _extract_year(text: str | None) -> int | None:
    if not text:
        return None
    match = YEAR_RE.search(str(text))
    if not match:
        return None
    year = int(match.group(1))
    return year if 1900 <= year <= 2099 else None


def _looks_like_sequel(result_title: str, target_title: str) -> bool:
    result = _normalize_title(result_title)
    target = _normalize_title(target_title)
    if not result.startswith(target) or len(result) <= len(target):
        return False
    tail = result[len(target) :]
    return bool(tail and tail[0].isdigit())


def _title_score(result_title: str, target_title: str, aliases: str = "") -> int:
    result = _normalize_title(result_title)
    if not result:
        return 0

    best = 0
    for target in _title_variants(target_title, aliases):
        if not target:
            continue
        if result == target:
            best = max(best, 100)
            continue
        if result.startswith(target) and not _looks_like_sequel(result_title, target_title):
            best = max(best, 88)
            continue
        if target.startswith(result) and len(result) >= 2 and not _looks_like_sequel(result_title, target_title):
            best = max(best, 92)
            continue
        if target in result and not _looks_like_sequel(result_title, target_title):
            best = max(best, 72)
            continue
        if result in target and len(result) >= 2 and not _looks_like_sequel(result_title, target_title):
            best = max(best, 85)
    return best


def _score_candidate(item: dict[str, Any], title: str, year: int | None, aliases: str = "") -> int:
    score = _title_score(item.get("title") or "", title, aliases)
    if score <= 0:
        return 0
    item_year = item.get("year")
    if year and item_year:
        if item_year == year:
            score += 45
        elif abs(item_year - year) == 1:
            score += 8
        else:
            score -= 35
    if _looks_like_sequel(item.get("title") or "", title):
        score -= 40
    if item.get("is_movie") is False:
        score -= 50
    return score


def _pick_best(
    items: list[dict[str, Any]],
    title: str,
    year: int | None,
    platform_hint: str | None = None,
    aliases: str = "",
) -> dict[str, Any] | None:
    best_item: dict[str, Any] | None = None
    best_score = 0
    for item in items:
        if platform_hint and item.get("platform_hint") != platform_hint:
            continue
        score = _score_candidate(item, title, year, aliases)
        if score > best_score:
            best_score = score
            best_item = item
    if best_item and best_score >= 75:
        return best_item
    return None


def _is_primarily_chinese(movie: dict) -> bool:
    languages = (movie.get("languages") or "").lower()
    return any(marker.lower() in languages for marker in CHINESE_LANGUAGE_MARKERS)


def _build_search_query(movie: dict) -> str:
    title = (movie.get("title") or "").strip()
    aliases = movie.get("aliases") or ""
    year = movie.get("release_year") or 0
    if not _is_primarily_chinese(movie):
        english = extract_english_title(title, aliases)
        if english:
            return f"{english} {year}".strip() if year else english
    primary = _primary_title(title, aliases)
    return f"{primary} {year}".strip() if year else primary


def _encode_query(query: str, platform: str) -> str:
    if platform in {"iqiyi", "youku", "mgtv"}:
        return quote(query, safe="")
    return quote(query)


def _fetch_json(url: str, *, params: dict | None = None, timeout: float = 5.0) -> dict | list | None:
    try:
        response = requests.get(url, params=params, headers=REQUEST_HEADERS, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def _parse_iqiyi_results(payload: dict | list | None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    docinfos = ((payload.get("data") or {}).get("docinfos")) or []
    items: list[dict[str, Any]] = []
    for doc in docinfos:
        album = doc.get("albumDocInfo") or {}
        channel = album.get("channel") or ""
        if "电影" not in channel:
            continue
        url = (album.get("albumLink") or "").replace("http://", "https://")
        if not url.startswith("https://"):
            continue
        release_date = album.get("releaseDate") or ""
        year = _extract_year(release_date[:4] if release_date else "")
        items.append(
            {
                "title": album.get("albumTitle") or "",
                "year": year,
                "url": url,
                "platform_hint": "iqiyi",
                "is_movie": True,
            }
        )
    return items


def _parse_youku_results(payload: dict | list | None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    items: list[dict[str, Any]] = []
    for comp in payload.get("pageComponentList") or []:
        common = comp.get("commonData") or {}
        title = ((common.get("titleDTO") or {}).get("displayName")) or ""
        feature = common.get("feature") or ""
        action = ((common.get("leftButtonDTO") or {}).get("action")) or {}
        url = action.get("value") or ""
        if not isinstance(url, str) or not url.startswith("http"):
            continue
        platform_hint = "youku"
        if "v.qq.com" in url:
            platform_hint = "tencent"
        elif "iqiyi.com" in url:
            platform_hint = "iqiyi"
        elif "mgtv.com" in url:
            platform_hint = "mgtv"
        elif "bilibili.com" in url:
            platform_hint = "bilibili"
        items.append(
            {
                "title": title,
                "year": _extract_year(feature),
                "url": url,
                "platform_hint": platform_hint,
                "is_movie": common.get("episodeType") == 1,
            }
        )
    return items


def _search_iqiyi(query: str) -> list[dict[str, Any]]:
    payload = _fetch_json(
        "https://search.video.iqiyi.com/o",
        params={"if": "html5", "key": query, "pageNum": 1, "pageSize": 12, "site": "iqiyi"},
    )
    return _parse_iqiyi_results(payload)


def _search_youku(query: str) -> list[dict[str, Any]]:
    payload = _fetch_json(
        "https://search.youku.com/api/search",
        params={"pg": 1, "keyword": query, "site": 1, "keytype": 1},
    )
    return _parse_youku_results(payload)


def _make_link(platform: str, label: str, url: str, *, direct: bool, matched_title: str | None = None) -> dict[str, Any]:
    link = {
        "platform": platform,
        "label": label,
        "url": url,
        "direct": direct,
    }
    if matched_title:
        link["matched_title"] = matched_title
    return link


def _fallback_link(platform: str, query: str) -> dict[str, Any]:
    encoded = _encode_query(query, platform)
    template = FALLBACK_SEARCH_URLS[platform]
    return _make_link(
        platform,
        PLATFORM_LABELS[platform],
        template.format(query=encoded),
        direct=False,
    )


def _resolve_direct_links(movie: dict, query: str) -> dict[str, dict[str, Any]]:
    title = (movie.get("title") or "").strip()
    aliases = movie.get("aliases") or ""
    year = movie.get("release_year") or None
    resolved: dict[str, dict[str, Any]] = {}

    with ThreadPoolExecutor(max_workers=2) as pool:
        iqiyi_future = pool.submit(_search_iqiyi, query)
        youku_future = pool.submit(_search_youku, query)
        iqiyi_items = iqiyi_future.result()
        youku_items = youku_future.result()

    iqiyi_best = _pick_best(iqiyi_items, title, year, "iqiyi", aliases)
    if iqiyi_best:
        resolved["iqiyi"] = _make_link(
            "iqiyi",
            PLATFORM_LABELS["iqiyi"],
            iqiyi_best["url"],
            direct=True,
            matched_title=iqiyi_best.get("title"),
        )

    youku_best = _pick_best(youku_items, title, year, "youku", aliases)
    if youku_best:
        resolved["youku"] = _make_link(
            "youku",
            PLATFORM_LABELS["youku"],
            youku_best["url"],
            direct=True,
            matched_title=youku_best.get("title"),
        )

    tencent_best = _pick_best(youku_items, title, year, "tencent", aliases)
    if tencent_best:
        resolved["tencent"] = _make_link(
            "tencent",
            PLATFORM_LABELS["tencent"],
            tencent_best["url"],
            direct=True,
            matched_title=tencent_best.get("title"),
        )

    return resolved


def _extract_douban_id(movie: dict) -> str | None:
    detail_url = movie.get("detail_url") or ""
    match = DOUBAN_ID_RE.search(detail_url)
    if match:
        return match.group(1)
    movie_id = movie.get("movie_id")
    if movie.get("source") == "douban" and movie_id:
        return str(movie_id)
    return None


def _tmdb_detail_page(tmdb_id: str, detail_url: str | None = None) -> dict[str, Any]:
    url = detail_url or f"https://www.themoviedb.org/movie/{tmdb_id}"
    return _make_link("tmdb_detail", "TMDB", url, direct=False)


def _append_detail_link(movie: dict, links: list[dict[str, Any]], tmdb_id: str | None) -> None:
    detail_url = (movie.get("detail_url") or "").strip()
    source = (movie.get("source") or "").strip().lower()

    if detail_url and TMDB_URL_RE.search(detail_url):
        links.append(_make_link("tmdb_detail", "TMDB", detail_url, direct=False))
        return
    if source == "tmdb" and tmdb_id:
        links.append(_tmdb_detail_page(tmdb_id, detail_url or None))
        return
    if detail_url and DOUBAN_ID_RE.search(detail_url):
        links.append(_make_link("douban", "豆瓣", detail_url, direct=False))
        return
    if source == "douban":
        douban_id = _extract_douban_id(movie)
        if douban_id:
            links.append(
                _make_link(
                    "douban",
                    "豆瓣",
                    detail_url or f"https://movie.douban.com/subject/{douban_id}/",
                    direct=False,
                )
            )
        return
    if detail_url:
        if TMDB_URL_RE.search(detail_url):
            links.append(_make_link("tmdb_detail", "TMDB", detail_url, direct=False))
        elif "douban.com" in detail_url:
            links.append(_make_link("douban", "豆瓣", detail_url, direct=False))


def resolve_watch_links(movie: dict) -> dict[str, Any]:
    movie_id = int(movie["movie_id"])
    cached = _watch_cache.get(movie_id)
    if cached and cached.get("_cache_version") == _WATCH_CACHE_VERSION:
        return {key: value for key, value in cached.items() if key != "_cache_version"}

    query = _build_search_query(movie)
    direct_map = _resolve_direct_links(movie, query)

    movie_id_direct = DIRECT_STREAMING_URLS.get(movie_id)
    if movie_id_direct:
        platform = "tencent" if "v.qq.com" in movie_id_direct else "streaming"
        direct_map[platform] = _make_link(
            platform if platform in PLATFORM_LABELS else "tencent",
            PLATFORM_LABELS.get(platform, "在线观看"),
            movie_id_direct,
            direct=True,
        )

    tmdb_id = resolve_tmdb_id(
        movie_id,
        title=movie.get("title") or "",
        aliases=movie.get("aliases") or "",
        release_year=movie.get("release_year"),
        detail_url=movie.get("detail_url"),
    )

    links: list[dict[str, Any]] = []
    for platform, _label in PLATFORM_META:
        if platform in direct_map:
            links.append(direct_map[platform])
        else:
            links.append(_fallback_link(platform, query))

    _append_detail_link(movie, links, tmdb_id)

    primary = None
    for platform, _label in PLATFORM_META:
        candidate = direct_map.get(platform)
        if candidate and candidate.get("direct"):
            primary = candidate
            break
    if not primary:
        for link in links:
            if link.get("platform") in PLATFORM_LABELS:
                primary = link
                break

    payload = {
        "primary_url": primary["url"] if primary else None,
        "primary_label": primary["label"] if primary else None,
        "primary_direct": bool(primary and primary.get("direct")),
        "links": links,
        "_cache_version": _WATCH_CACHE_VERSION,
    }
    _watch_cache[movie_id] = payload
    return {key: value for key, value in payload.items() if key != "_cache_version"}
