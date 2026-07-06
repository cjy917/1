from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
CS1_ROOT = PROJECT_DIR.parent.parent
# 兼容 cs1/movie-system/movie-system 与 FYWZ/movie-system 两种目录布局
ROOT_DIR = CS1_ROOT if (CS1_ROOT / "films_data").exists() else PROJECT_DIR.parent

SPARK_DIR = PROJECT_DIR / "spark"
SPARK_OUTPUT_DIR = SPARK_DIR / "output"
SPARK_DATA_DIR = SPARK_DIR / "data"
SPARK_MOVIES_CATALOG = SPARK_DATA_DIR / "movies_catalog.ndjson"
SPARK_HISTORY_RATINGS = SPARK_DATA_DIR / "ratings_history.ndjson"
SPARK_WEB_RATINGS = SPARK_DATA_DIR / "ratings_web.ndjson"
# 爬虫评分 CSV 目录（仅首次 seed_crawled_ratings 导入 SQLite 时使用）
FILMS_RATINGS_DIR = ROOT_DIR / "films_data" / "ratings" / "ratings.csv"

# 混合推荐权重
WEIGHT_ALS = 0.7
WEIGHT_GRAPHX = 0.2
WEIGHT_CONTENT = 0.1
RECOMMEND_TOP_N = 12

# Ubuntu VM Spark 网关（用户点「刷新推荐」时同步 ratings 并触发批处理）
SPARK_VM_URL = os.environ.get("SPARK_VM_URL", "http://192.168.111.128:5001")
SPARK_VM_ENABLED = os.environ.get("SPARK_VM_ENABLED", "true").lower() in ("1", "true", "yes")
SPARK_USER_OFFSET = 1_000_000
SPARK_RECOMPUTE_TIMEOUT = int(os.environ.get("SPARK_RECOMPUTE_TIMEOUT", "600"))
SPARK_RECOMPUTE_POLL_INTERVAL = int(os.environ.get("SPARK_RECOMPUTE_POLL_INTERVAL", "5"))

SECRET_KEY = os.environ.get("SECRET_KEY", "spark-movie-recommend-2026")
SQLALCHEMY_DATABASE_URI = f"sqlite:///{(BASE_DIR / 'app.db').as_posix()}"
SQLALCHEMY_TRACK_MODIFICATIONS = False

MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "123456")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "movies_db")

# 爬虫评分 CSV 目录（仅首次 seed_crawled_ratings 导入 SQLite 时使用）
# 运行时评分以 SQLite crawled_ratings + user_ratings 为准

PICTURE_DIRS = [
    ROOT_DIR / "posters",
    ROOT_DIR / "posters" / "posters",
    ROOT_DIR / "picture",
    ROOT_DIR / "picture" / "output" / "posters",
    ROOT_DIR / "films_data" / "picture",
    PROJECT_DIR / "picture",
]
# 同机部署时回退到 FYWZ 海报目录（cover_path 多为 ./picture/p*.webp）
_fywz_posters = ROOT_DIR.parent / "FYWZ" / "posters"
if _fywz_posters.exists() and _fywz_posters not in PICTURE_DIRS:
    PICTURE_DIRS.append(_fywz_posters)

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
POSTER_THUMB_DIR = MEDIA_DIR / "poster_thumbs"

# 本地正片文件名映射：movie_id -> videos/ 下的文件名（非 {movie_id}.mp4 时使用）
NEZHA_LOCAL_VIDEO = "2025.1080p.WEB-DL.H264.AAC.mp4"
LOCAL_VIDEO_FILES: dict[int, str] = {
    26794435: NEZHA_LOCAL_VIDEO,  # 哪吒之魔童降世（当前为本地闹海正片）
    980477: NEZHA_LOCAL_VIDEO,    # 哪吒之魔童闹海
}

SECRETS_FILE = PROJECT_DIR / "secrets.local"


def _load_secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if SECRETS_FILE.exists():
        for raw in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == name:
                return v.strip().strip('"').strip("'")
    return ""


def load_tmdb_api_key() -> str:
    return _load_secret("TMDB_API_KEY")


TMDB_API_KEY = load_tmdb_api_key()

# HTTP/HTTPS/SOCKS 代理：支持环境变量或 secrets.local 覆盖，默认空（直连）
HTTP_PROXY = _load_secret("HTTP_PROXY") or os.environ.get("HTTP_PROXY", "")
HTTPS_PROXY = _load_secret("HTTPS_PROXY") or os.environ.get("HTTPS_PROXY", "")
SOCKS_PROXY = _load_secret("SOCKS_PROXY") or os.environ.get("SOCKS_PROXY", "")
NO_PROXY = (
    _load_secret("NO_PROXY")
    or os.environ.get("NO_PROXY", "localhost,127.0.0.1,::1")
)

# ── AI 助手（硅基流动 SiliconFlow OpenAI 兼容接口）──
# 默认关闭：只有显式配置了 API Key 才启用上游 LLM 调用
AI_ASSISTANT_ENABLED = os.environ.get(
    "AI_ASSISTANT_ENABLED",
    "false",
).lower() not in ("0", "false", "no", "off", "")
AI_ASSISTANT_API_KEY = _load_secret("AI_ASSISTANT_API_KEY")
if AI_ASSISTANT_API_KEY:
    AI_ASSISTANT_ENABLED = True
AI_ASSISTANT_BASE_URL = os.environ.get(
    "AI_ASSISTANT_BASE_URL",
    "https://api.siliconflow.cn/v1",
)
AI_ASSISTANT_MODEL = os.environ.get(
    "AI_ASSISTANT_MODEL",
    "Qwen/Qwen2.5-7B-Instruct",
)
AI_ASSISTANT_TIMEOUT = int(os.environ.get("AI_ASSISTANT_TIMEOUT", "60"))
AI_ASSISTANT_MAX_HISTORY = int(os.environ.get("AI_ASSISTANT_MAX_HISTORY", "10"))

# ── AI 联网搜索（Tavily）──
# 内部项目默认「只查内部数据库」，避免外部 API 依赖；若要打开请在 secrets.local 配 AI_WEB_SEARCH_API_KEY
AI_WEB_SEARCH_ENABLED = (
    os.environ.get("AI_WEB_SEARCH_ENABLED", "false").lower()
    in ("1", "true", "yes", "on")
)
AI_WEB_SEARCH_API_KEY = _load_secret("AI_WEB_SEARCH_API_KEY")
if AI_WEB_SEARCH_API_KEY:
    AI_WEB_SEARCH_ENABLED = True
AI_WEB_SEARCH_PROVIDER = os.environ.get("AI_WEB_SEARCH_PROVIDER", "tavily")
AI_WEB_SEARCH_MAX_RESULTS = int(os.environ.get("AI_WEB_SEARCH_MAX_RESULTS", "3"))
# info source 策略：internal_only（只查内部 DB，默认）/ prefer_internal（内部无再联网）/ both
AI_INFO_SOURCE_STRATEGY = os.environ.get("AI_INFO_SOURCE_STRATEGY", "internal_only")

