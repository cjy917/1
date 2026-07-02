"""从 MySQL 导出电影特征 NDJSON，供 Spark TF-IDF 内容推荐使用。"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from services.catalog_service import export_spark_movies_catalog_file


def export_catalog(output_path: Path | None = None) -> int:
    app = create_app()
    with app.app_context():
        return export_spark_movies_catalog_file(output_path)


if __name__ == "__main__":
    export_catalog()
