import re

from services.http_client import external_get

from config import TMDB_API_KEY

TMDB_ID_RE = re.compile(r"/movie/(\d+)")
SEARCH_TIMEOUT = 12

_tmdb_id_cache: dict[str, str] = {}


def extract_tmdb_id(movie_id: str | int, detail_url: str | None = None) -> str:
    if detail_url:
        match = TMDB_ID_RE.search(detail_url)
        if match:
            return match.group(1)
    return str(movie_id)


def extract_english_title(title: str, aliases: str | None = None) -> str:
    def english_chunks(text: str) -> list[str]:
        matches = re.findall(r"[A-Za-z][A-Za-z0-9\s':\-,\.!&]{1,}", text or "")
        return [m.strip(" .,-") for m in matches if len(m.strip(" .,-")) >= 3]

    def best_chunk(parts: list[str]) -> str | None:
        chunks = []
        for part in parts:
            chunks.extend(english_chunks(part))
        if not chunks:
            return None
        return max(chunks, key=len)

    if aliases:
        alias_parts = [part.strip() for part in aliases.split("|") if part.strip()]
        endgame_aliases = [p for p in alias_parts if re.search(r"endgame", p, re.I)]
        chunk = best_chunk(endgame_aliases)
        if chunk:
            return chunk
        non_infinity = [p for p in alias_parts if "infinity war" not in p.lower()]
        chunk = best_chunk(non_infinity)
        if chunk:
            return chunk

    if title:
        chunk = best_chunk(re.split(r"[：/|]", title))
        if chunk:
            return chunk

    if aliases:
        chunk = best_chunk(aliases.split("|"))
        if chunk:
            return chunk

    return best_chunk([title or ""]) or (title.strip() if title else "")


def _cache_key(title: str, release_year: int | None) -> str:
    return f"{title}|{release_year or ''}"


def search_tmdb_id(title: str, aliases: str = "", release_year: int | None = None) -> str | None:
    if not TMDB_API_KEY:
        return None

    cache_key = _cache_key(title, release_year)
    if cache_key in _tmdb_id_cache:
        return _tmdb_id_cache[cache_key]

    queries: list[tuple[str, str]] = []
    en = extract_english_title(title, aliases)
    if en:
        queries.append((en, "en-US"))
    if title.strip():
        queries.append((title.strip(), "zh-CN"))
    if aliases:
        for part in aliases.split("|"):
            part = part.strip()
            if part and (part, "zh-CN") not in [(q, l) for q, l in queries]:
                queries.append((part, "zh-CN"))

    headers = {"User-Agent": "FYWZ-Movies/1.0"}
    for query, language in queries[:2]:
        try:
            params: dict = {
                "api_key": TMDB_API_KEY,
                "query": query,
                "language": language,
                "include_adult": "false",
            }
            if release_year:
                params["primary_release_year"] = int(release_year)
            response = external_get(
                "https://api.themoviedb.org/3/search/movie",
                params=params,
                headers=headers,
                timeout=SEARCH_TIMEOUT,
            )
            response.raise_for_status()
            results = response.json().get("results", [])
            if not results:
                continue

            best_id = None
            if release_year:
                for item in results:
                    year = (item.get("release_date") or "")[:4]
                    if year.isdigit() and abs(int(year) - int(release_year)) <= 1:
                        best_id = str(item["id"])
                        break
            if not best_id:
                best_id = str(results[0]["id"])

            _tmdb_id_cache[cache_key] = best_id
            return best_id
        except Exception:
            continue
    return None


def resolve_tmdb_id(
    movie_id: str | int,
    title: str = "",
    aliases: str = "",
    release_year: int | None = None,
    detail_url: str | None = None,
) -> str | None:
    if detail_url and TMDB_ID_RE.search(detail_url):
        return extract_tmdb_id(movie_id, detail_url)

    searched = search_tmdb_id(title, aliases, release_year)
    if searched:
        return searched

    fallback = extract_tmdb_id(movie_id, detail_url)
    if fallback and fallback != str(movie_id):
        return fallback
    return searched


BLOCKED_BACKDROP_PATHS = frozenset({
    "/gZ2kyF53ttTxIRcEV51gs8Jw9Lz.jpg",  # Hamilton 视频会议拼图
})


def fetch_tmdb_backdrop_url(tmdb_id: str) -> str | None:
    if not TMDB_API_KEY or not tmdb_id:
        return None
    try:
        response = external_get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}",
            params={"api_key": TMDB_API_KEY, "language": "zh-CN"},
            headers={"User-Agent": "FYWZ-Movies/1.0"},
            timeout=SEARCH_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        path = data.get("backdrop_path")
        if not path or path in BLOCKED_BACKDROP_PATHS:
            return None
        return f"https://image.tmdb.org/t/p/w1280{path}"
    except Exception:
        return None
