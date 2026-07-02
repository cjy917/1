#!/usr/bin/env python3
"""
TMDB 电影数据爬虫扩展模块
用于补充爬取电影数据，目标超过 5000 条记录。

使用方法:
  python tmdb_crawler.py --api-key YOUR_TMDB_API_KEY --pages 50

注意: 请遵守 TMDB API 使用条款，控制请求频率，避免对网站造成压力。
"""

import argparse
import csv
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "merged"
POSTER_DIR = OUTPUT_DIR / "posters"


class TMDBCrawler:
    BASE_URL = "https://api.themoviedb.org/3"

    def __init__(self, api_key: str, language: str = "zh-CN"):
        self.api_key = api_key
        self.language = language
        self.session = requests.Session()

    def _get(self, path: str, params: dict | None = None) -> dict:
        params = params or {}
        params["api_key"] = self.api_key
        params["language"] = self.language
        response = self.session.get(f"{self.BASE_URL}{path}", params=params, timeout=30)
        response.raise_for_status()
        time.sleep(0.25)
        return response.json()

    def fetch_discover_page(self, page: int) -> list[dict]:
        data = self._get(
            "/discover/movie",
            {
                "sort_by": "popularity.desc",
                "page": page,
                "include_adult": "false",
            },
        )
        return data.get("results", [])

    def fetch_movie_detail(self, movie_id: int) -> dict:
        return self._get(f"/movie/{movie_id}", {"append_to_response": "credits,reviews"})

    def download_poster(self, poster_path: str, movie_id: int, title: str) -> str:
        if not poster_path:
            return ""
        POSTER_DIR.mkdir(parents=True, exist_ok=True)
        url = f"https://image.tmdb.org/t/p/w500{poster_path}"
        filename = f"{movie_id}_{title[:20].replace('/', '_')}.jpg"
        target = POSTER_DIR / filename
        if not target.exists():
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            target.write_bytes(response.content)
            time.sleep(0.2)
        return f"posters/{filename}"

    def crawl(self, pages: int = 20) -> list[dict]:
        movies = []
        existing_ids = set()
        csv_path = OUTPUT_DIR / "movies.csv"
        if csv_path.exists():
            with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle):
                    existing_ids.add(str(row.get("电影ID", "")))

        for page in range(1, pages + 1):
            print(f"Crawling page {page}/{pages}...")
            for item in self.fetch_discover_page(page):
                movie_id = str(item["id"])
                if movie_id in existing_ids:
                    continue
                detail = self.fetch_movie_detail(item["id"])
                title = detail.get("title") or detail.get("original_title") or ""
                poster = self.download_poster(detail.get("poster_path"), item["id"], title)
                movies.append(
                    {
                        "电影ID": movie_id,
                        "中文名称": title,
                        "评分": str(detail.get("vote_average", 0)),
                        "评分总人数": str(detail.get("vote_count", 0)),
                        "上映日期": detail.get("release_date", ""),
                        "上映年份": (detail.get("release_date") or "")[:4],
                        "导演": ",".join(
                            c["name"]
                            for c in detail.get("credits", {}).get("crew", [])
                            if c.get("job") == "Director"
                        ),
                        "编剧": "",
                        "主演": ",".join(c["name"] for c in detail.get("credits", {}).get("cast", [])[:8]),
                        "电影别名": detail.get("original_title", ""),
                        "简介": detail.get("overview", ""),
                        "详情页链接": f"https://www.themoviedb.org/movie/{movie_id}",
                        "影片语言": ",".join(
                            lang.get("english_name", "") for lang in detail.get("spoken_languages", [])
                        ),
                        "影片类型": ",".join(g["name"] for g in detail.get("genres", [])),
                        "片长": str(detail.get("runtime") or ""),
                        "评论内容": "",
                        "制片国家/地区": ",".join(c["name"] for c in detail.get("production_countries", [])),
                        "获奖情况": "",
                        "影评数": 0,
                        "封面路径": poster,
                        "视频地址": "",
                    }
                )
                existing_ids.add(movie_id)
        return movies

    def append_to_csv(self, movies: list[dict]) -> None:
        if not movies:
            print("No new movies to append.")
            return
        csv_path = OUTPUT_DIR / "movies.csv"
        fieldnames = list(movies[0].keys())
        file_exists = csv_path.exists()
        with csv_path.open("a", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerows(movies)
        json_path = OUTPUT_DIR / "movies.json"
        existing = []
        if json_path.exists():
            existing = json.loads(json_path.read_text(encoding="utf-8"))
        existing.extend(movies)
        json_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Appended {len(movies)} movies. Total in JSON: {len(existing)}")


def main():
    parser = argparse.ArgumentParser(description="TMDB movie crawler extension")
    parser.add_argument("--api-key", required=True, help="TMDB API Key")
    parser.add_argument("--pages", type=int, default=20, help="Number of pages to crawl")
    args = parser.parse_args()

    crawler = TMDBCrawler(args.api_key)
    movies = crawler.crawl(pages=args.pages)
    crawler.append_to_csv(movies)


if __name__ == "__main__":
    main()
