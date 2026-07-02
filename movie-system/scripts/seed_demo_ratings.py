"""生成演示用户评分数据，供 Spark ALS/GraphX 推荐任务使用。"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from models import Movie, Rating, User, db


def seed_demo_ratings():
    app = create_app()
    with app.app_context():
        for name in ["demo", "alice", "bob", "carol", "david"]:
            if not User.query.filter_by(username=name).first():
                user = User(username=name, email=f"{name}@test.com")
                user.set_password("123456")
                db.session.add(user)
        db.session.commit()
        users = User.query.all()

        movies = Movie.query.order_by(Movie.rating.desc()).limit(200).all()
        count = 0
        for user in users:
            for idx, movie in enumerate(movies):
                if idx % (user.id + 2) != 0:
                    continue
                score = round(max(1.0, min(10.0, movie.rating + (user.id % 3) - 1)), 1)
                existing = Rating.query.filter_by(user_id=user.id, movie_id=movie.id).first()
                if existing:
                    continue
                db.session.add(Rating(user_id=user.id, movie_id=movie.id, score=score))
                count += 1
        db.session.commit()
        print(f"Seeded {count} demo ratings for {len(users)} users")


if __name__ == "__main__":
    seed_demo_ratings()
    from import_data import export_ratings_for_spark
    export_ratings_for_spark(Path(__file__).resolve().parents[1] / "spark" / "data" / "ratings.json")
