import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
ROOT_DIR = PROJECT_DIR.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "spark-movie-recommend-2026")
SQLALCHEMY_DATABASE_URI = f"sqlite:///{(BASE_DIR / 'app.db').as_posix()}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "123456")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "movies_db")

RATINGS_CSV = ROOT_DIR / "films_data" / "ratings" / "ratings.csv" / "part-00000-7a865d44-e3a2-439e-8431-068b3f538be8-c000.csv"
if not RATINGS_CSV.exists():
    RATINGS_CSV = ROOT_DIR / "ratings" / "ratings.csv" / "part-00000-7a865d44-e3a2-439e-8431-068b3f538be8-c000.csv"

PICTURE_DIRS = [
    ROOT_DIR / "posters",
    ROOT_DIR / "picture",
    ROOT_DIR / "picture" / "output" / "posters",
    ROOT_DIR / "films_data" / "picture",
    PROJECT_DIR / "picture",
]

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 60

# 首页 Hero 轮播排除
BANNER_EXCLUDED_MOVIE_IDS = frozenset({
    34856004,  # 丹尼尔·斯洛斯：X
    35424716,  # 容祖儿 PRETTY CRAZY 演唱会
    35231832,  # 鬼灭之刃：那田蜘蛛山篇
    30484534,  # 摇滚红与黑
})
# 补入 Hero 的替换电影（按顺序追加，需有本地封面）
BANNER_PRIORITY_MOVIE_IDS = (
    27010768,  # 寄生虫
    490132,    # 绿皮书
)
BANNER_SIZE = 6
BANNER_CANDIDATE_POOL = 40
# 本地预告预下载：热门电影栏只下前 N 部（Hero 仍按 BANNER_SIZE）
POPULAR_TRAILER_DOWNLOAD_SIZE = 6

FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"

VIDEO_DIR = ROOT_DIR / "videos"
TRAILER_DIR = ROOT_DIR / "trailers"
MEDIA_DIR = PROJECT_DIR / "media"

# 本地正片文件名映射：movie_id -> videos/ 下的文件名（非 {movie_id}.mp4 时使用）
LOCAL_VIDEO_FILES: dict[int, str] = {}

# 国内可访问的演示 MP4，用于无本地文件时的兜底播放
DEMO_MOVIE_MP4 = "https://www.w3school.com.cn/example/html5/mov_bbb.mp4"
DEMO_TRAILER_MP4 = "https://www.w3school.com.cn/example/html5/mov_bbb.mp4"

SECRETS_FILE = PROJECT_DIR / "secrets.local"


def load_tmdb_api_key() -> str:
    key = os.environ.get("TMDB_API_KEY", "").strip()
    if key:
        return key
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TMDB_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


TMDB_API_KEY = load_tmdb_api_key()
