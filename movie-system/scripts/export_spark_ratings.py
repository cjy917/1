"""从 SQLite 导出评分 NDJSON，供 Spark ALS / GraphX / TF-IDF 使用。"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from services.ratings_service import export_spark_ratings_file


def export_ratings(output_path: Path | None = None) -> int:
    app = create_app()
    with app.app_context():
        return export_spark_ratings_file(output_path)


if __name__ == "__main__":
    export_ratings()
