import csv
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from config import DATA_DIR
from models import Movie, db


def parse_int(value, default=0):
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def parse_float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def import_from_csv(csv_path: Path) -> int:
    app = create_app()
    count = 0
    with app.app_context():
        db.create_all()
        if Movie.query.count() > 0:
            print(f"Database already has {Movie.query.count()} movies, skipping import.")
            return Movie.query.count()

        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                movie = Movie(
                    movie_id=str(row.get("电影ID", "")).strip(),
                    title=(row.get("中文名称") or "").strip(),
                    rating=parse_float(row.get("评分")),
                    rating_count=parse_int(row.get("评分总人数")),
                    release_date=(row.get("上映日期") or "").strip(),
                    release_year=parse_int(row.get("上映年份"), None),
                    director=(row.get("导演") or "").strip(),
                    writer=(row.get("编剧") or "").strip(),
                    actors=(row.get("主演") or "").strip(),
                    aliases=(row.get("电影别名") or "").strip(),
                    summary=(row.get("简介") or "").strip(),
                    detail_url=(row.get("详情页链接") or "").strip(),
                    language=(row.get("影片语言") or "").strip(),
                    genres=(row.get("影片类型") or "").strip(),
                    duration=parse_int(row.get("片长")),
                    crawled_reviews=(row.get("评论内容") or "").strip(),
                    country=(row.get("制片国家/地区") or "").strip(),
                    awards=(row.get("获奖情况") or "").strip(),
                    review_count=parse_int(row.get("影评数")),
                    poster_path=(row.get("封面路径") or "").replace("\\", "/"),
                    video_url=(row.get("视频地址") or row.get("video_url") or "").strip(),
                )
                db.session.add(movie)
                count += 1
                if count % 500 == 0:
                    db.session.commit()
                    print(f"Imported {count} movies...")
        db.session.commit()
    return count


def export_ratings_for_spark(output_path: Path) -> None:
    app = create_app()
    with app.app_context():
        from models import Rating, User

        rows = []
        for rating in Rating.query.all():
            rows.append(
                {
                    "userId": rating.user_id,
                    "movieId": rating.movie.movie_id,
                    "rating": rating.score,
                }
            )

        if not rows:
            demo_users = User.query.limit(5).all()
            top_movies = Movie.query.order_by(Movie.rating.desc()).limit(30).all()
            for user in demo_users:
                for idx, movie in enumerate(top_movies):
                    rows.append({"userId": user.id, "movieId": movie.movie_id, "rating": max(1.0, 5.0 - idx * 0.1)})

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=2)
        print(f"Exported {len(rows)} ratings to {output_path}")


if __name__ == "__main__":
    csv_file = DATA_DIR / "movies.csv"
    if not csv_file.exists():
        raise SystemExit(f"CSV not found: {csv_file}")
    total = import_from_csv(csv_file)
    print(f"Import finished: {total} movies")
    export_ratings_for_spark(BASE_DIR.parent / "spark" / "data" / "ratings.json")
