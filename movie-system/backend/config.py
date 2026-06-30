"""
FYWZ 电影推荐系统 - 配置文件

【双数据库配置】
  SQLite: 用户数据（users, user_ratings, favorites 等）
  MySQL:  电影数据（movies 表，6766条记录）

【推荐系统配置】
  混合推荐权重：ALS(70%) + GraphX(20%) + Content(10%)
  Spark VM: Ubuntu 虚拟机批处理（用户触发刷新）

【文件目录结构】
  ROOT_DIR/
    films_data/          # 爬虫数据目录
      ratings/           # 爬虫评分 CSV
      picture/           # 海报图片
    posters/             # 海报目录（多路径兼容）
    videos/              # 本地正片视频
    trailers/            # 本地预告片
"""

import os
from pathlib import Path

# ==================== 目录结构 ====================
BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
CS1_ROOT = PROJECT_DIR.parent.parent
# 兼容 cs1/movie-system2/movie-system2 与 FYWZ/movie-system2 两种目录布局
ROOT_DIR = CS1_ROOT if (CS1_ROOT / "films_data").exists() else PROJECT_DIR.parent

SPARK_DIR = PROJECT_DIR / "spark"
SPARK_OUTPUT_DIR = SPARK_DIR / "output"
SPARK_DATA_DIR = SPARK_DIR / "data"
FILMS_RATINGS_DIR = ROOT_DIR / "films_data" / "ratings" / "ratings.csv"

# ==================== 推荐系统权重配置 ====================
# 混合推荐算法权重分配（总和为1）
WEIGHT_ALS = 0.7       # NMF-ALS 协同过滤权重（主要算法）
WEIGHT_GRAPHX = 0.2    # GraphX 社交关系推荐权重
WEIGHT_CONTENT = 0.1   # TF-IDF 内容推荐权重（补充）
RECOMMEND_TOP_N = 12   # 推荐返回数量

# ==================== Spark VM 配置 ====================
# Ubuntu VM Spark 网关（用户点「刷新推荐」时同步 ratings 并触发批处理）
SPARK_VM_URL = os.environ.get("SPARK_VM_URL", "http://192.168.111.128:5001")
SPARK_VM_ENABLED = os.environ.get("SPARK_VM_ENABLED", "true").lower() in ("1", "true", "yes")
SPARK_USER_OFFSET = 1_000_000  # Spark 用户ID偏移量（避免与爬虫用户ID冲突）
SPARK_RECOMPUTE_TIMEOUT = int(os.environ.get("SPARK_RECOMPUTE_TIMEOUT", "600"))  # 超时时间（秒）
SPARK_RECOMPUTE_POLL_INTERVAL = int(os.environ.get("SPARK_RECOMPUTE_POLL_INTERVAL", "5"))  # 轮询间隔（秒）

# ==================== Flask 应用配置 ====================
SECRET_KEY = os.environ.get("SECRET_KEY", "spark-movie-recommend-2026")  # Session加密密钥
SQLALCHEMY_DATABASE_URI = f"sqlite:///{(BASE_DIR / 'app.db').as_posix()}"  # SQLite 用户数据库路径
SQLALCHEMY_TRACK_MODIFICATIONS = False  # 禁用修改追踪（提升性能）

# ==================== MySQL 数据库配置（movies 表） ====================
# movies 表存储在 MySQL 中，通过 PyMySQL 直接查询
# 表结构定义在：../../../movies_backup.sql
MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
MYSQL_USER = os.environ.get("MYSQL_USER", "root")
MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "123456")
MYSQL_DATABASE = os.environ.get("MYSQL_DATABASE", "movies_db")

# ==================== 爬虫评分数据路径 ====================
# 多路径兼容：优先查找标准路径，不存在则回退
RATINGS_CSV = ROOT_DIR / "films_data" / "ratings" / "ratings.csv" / "part-00000-7a865d44-e3a2-439e-8431-068b3f538be8-c000.csv"
if not RATINGS_CSV.exists():
    RATINGS_CSV = ROOT_DIR / "ratings" / "ratings.csv" / "part-00000-7a865d44-e3a2-439e-8431-068b3f538be8-c000.csv"
if not RATINGS_CSV.exists() and FILMS_RATINGS_DIR.exists():
    csv_parts = sorted(FILMS_RATINGS_DIR.glob("part-*.csv"))
    if csv_parts:
        RATINGS_CSV = csv_parts[0]

# ==================== 海报图片目录（多路径兼容） ====================
# 按优先级顺序查找海报文件
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

# ==================== 分页配置 ====================
DEFAULT_PAGE_SIZE = 20   # 默认每页数量
MAX_PAGE_SIZE = 60       # 最大每页数量（防止恶意请求）

# ==================== 首页 Hero 轮播配置 ====================
# 排除不适合作为轮播的电影（演唱会、纪录片等）
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
BANNER_SIZE = 6              # Hero 轮播数量
BANNER_CANDIDATE_POOL = 40   # 候选池大小（从高分电影中随机选取）
# 本地预告预下载：热门电影栏只下前 N 部（Hero 仍按 BANNER_SIZE）
POPULAR_TRAILER_DOWNLOAD_SIZE = 6

# ==================== 前端静态文件配置 ====================
FRONTEND_DIST = PROJECT_DIR / "frontend" / "dist"

# ==================== 视频文件目录 ====================
VIDEO_DIR = ROOT_DIR / "videos"       # 本地正片视频目录
TRAILER_DIR = ROOT_DIR / "trailers"   # 本地预告片目录
MEDIA_DIR = PROJECT_DIR / "media"     # 媒体文件目录

# ==================== 本地正片文件名映射 ====================
# movie_id -> videos/ 下的文件名（非 {movie_id}.mp4 时使用）
NEZHA_LOCAL_VIDEO = "2025.1080p.WEB-DL.H264.AAC.mp4"
LOCAL_VIDEO_FILES: dict[int, str] = {
    26794435: NEZHA_LOCAL_VIDEO,  # 哪吒之魔童降世（当前为本地闹海正片）
    980477: NEZHA_LOCAL_VIDEO,    # 哪吒之魔童闹海
}

# ==================== 密钥文件 ====================
SECRETS_FILE = PROJECT_DIR / "secrets.local"


def load_tmdb_api_key() -> str:
    """
    加载 TMDb API 密钥
    
    优先级：
      1. 环境变量 TMDB_API_KEY
      2. secrets.local 文件中 TMDB_API_KEY=xxx 行
    
    Returns:
        TMDb API 密钥（空字符串表示未配置）
    """
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