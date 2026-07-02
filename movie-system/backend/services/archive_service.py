from urllib.parse import quote

import requests

from services.tmdb_meta import extract_english_title

ARCHIVE_HEADERS = {"User-Agent": "FYWZ-Movies/1.0 (Educational Project)"}


def _pick_best_mp4(files: list[dict]) -> str | None:
    mp4_files = [
        f
        for f in files
        if f.get("name", "").lower().endswith(".mp4")
        and str(f.get("size", "0")).isdigit()
        and int(f["size"]) > 1024 * 1024
    ]
    if not mp4_files:
        return None
    mp4_files.sort(key=lambda item: int(item.get("size", 0)), reverse=True)
    return mp4_files[0]["name"]


def fetch_archive_video_url(title: str, aliases: str = "") -> str | None:
    titles: list[str] = []
    en = extract_english_title(title, aliases)
    if en:
        titles.append(en)
    if title.strip() and title.strip() not in titles:
        titles.append(title.strip())
    if aliases:
        for alias in aliases.split("|"):
            alias = alias.strip()
            if alias and alias not in titles:
                titles.append(alias)

    for name in titles[:4]:
        try:
            response = requests.get(
                "https://archive.org/advancedsearch.php",
                params={
                    "q": f'title:"{name}" AND mediatype:movies',
                    "fl": "identifier,title",
                    "output": "json",
                    "rows": 5,
                },
                headers=ARCHIVE_HEADERS,
                timeout=8,
            )
            response.raise_for_status()
            docs = response.json().get("response", {}).get("docs", [])
            for doc in docs:
                identifier = doc.get("identifier")
                if not identifier:
                    continue
                meta = requests.get(
                    f"https://archive.org/metadata/{identifier}",
                    headers=ARCHIVE_HEADERS,
                    timeout=8,
                ).json()
                filename = _pick_best_mp4(meta.get("files", []))
                if filename:
                    return f"https://archive.org/download/{identifier}/{quote(filename)}"
        except Exception:
            continue
    return None
