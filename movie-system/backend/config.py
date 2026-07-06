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

# 本地正片文件名映射：movie_id -> videos/ 下的文件名（非 {movie_id}.mp4 时使用）
NEZHA_LOCAL_VIDEO = "2025.1080p.WEB-DL.H264.AAC.mp4"
LOCAL_VIDEO_FILES: dict[int, str] = {
    26794435: NEZHA_LOCAL_VIDEO,  # 哪吒之魔童降世（当前为本地闹海正片）
    980477: NEZHA_LOCAL_VIDEO,    # 哪吒之魔童闹海
}

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


def _load_secret_from_file(key: str) -> str:
    env_val = os.environ.get(key, "").strip()
    if env_val:
        return env_val
    if SECRETS_FILE.exists():
        for line in SECRETS_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


AI_ASSISTANT_ENABLED = os.environ.get("AI_ASSISTANT_ENABLED", "true").lower() in ("1", "true", "yes")
AI_ASSISTANT_API_BASE = os.environ.get("AI_ASSISTANT_API_BASE", "https://api.siliconflow.cn/v1")
AI_ASSISTANT_API_KEY = _load_secret_from_file("AI_ASSISTANT_API_KEY")
AI_ASSISTANT_MODEL = os.environ.get("AI_ASSISTANT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
AI_ASSISTANT_TIMEOUT = int(os.environ.get("AI_ASSISTANT_TIMEOUT", "90"))
AI_ASSISTANT_MAX_TOKENS = int(os.environ.get("AI_ASSISTANT_MAX_TOKENS", "1024"))
AI_ASSISTANT_SYSTEM_PROMPT = os.environ.get(
    "AI_ASSISTANT_SYSTEM_PROMPT",
    "【重要：必须严格遵守语言规则】\n"
    "你是一个中文电影推荐系统的AI智能语音助手，名叫「小影」。\n"
    "语言规则（最高优先级，任何情况下都要遵守）：\n"
    "1. 无论用户使用什么语言提问，你的所有回答必须100%使用【简体中文】，禁止出现任何英文、韩文、日文、法文等其他语言的单词或句子。\n"
    "2. 外国人名、电影名请使用官方通用的中文译名，不要夹杂原文。例如用「流浪地球」不要用「The Wandering Earth」，用「喜剧」不要用「comedy」。\n"
    "3. 即使用户要求你用其他语言回答，也要礼貌地说明：「抱歉，我只能使用中文回答您的问题。」然后继续用中文。\n"
    "业务规则：\n"
    "- 用友好、简洁的中文回答用户关于电影的问题，包括电影推荐、电影信息查询、评分分析等。\n"
    "- 回答要口语化、短句、适合语音播放，每段不超过200字。\n"
    "- 如果用户问非电影相关问题，可以礼貌用中文回答。\n"
    "【国家/地区概念定义 - 必须严格遵守，违反即视为错误回答】\n"
    "1. 用户说的「欧美电影」「西方电影」「好莱坞电影」= 以下25个国家：美国、英国、法国、德国、意大利、西班牙、加拿大、澳大利亚、爱尔兰、比利时、荷兰、瑞士、瑞典、挪威、丹麦、芬兰、奥地利、葡萄牙、希腊、冰岛、卢森堡、波兰、捷克、匈牙利、新西兰。\n"
    "   → 绝对不包括：韩国、日本、中国大陆、中国香港、中国台湾、泰国、印度、越南、新加坡、土耳其、以色列、俄罗斯等非欧美文化圈国家。\n"
    "   → 如果系统返回的候选电影里混入了韩国/日本/亚洲电影，必须剔除并重新选，绝对不要出现在欧美推荐列表中。\n"
    "2. 「韩国电影」= 仅韩国（别名：南韩/South Korea）。\n"
    "   → 以下都是韩国电影，绝对不能归入欧美：《寄生虫》《釜山行》《出租车司机》《杀人回忆》《素媛》《熔炉》《辩护人》《82年生的金智英》《燃烧》《恶人传》《极限职业》《南山的部长们》等。\n"
    "3. 「日本电影」= 仅日本，绝对不能归入欧美或韩国。\n"
    "4. 「华语电影」/「国产电影」/「内地电影」/「中文电影」= 中国大陆、中国香港、中国台湾、新加坡（即以中文为主流语言的地区），绝对不能混入欧美或日韩电影。\n"
    "5. 如果用户明确指定了地区（如「2020年的欧美电影」「韩国悬疑片」），推荐结果必须100%符合该地区条件。该地区下若符合条件的电影少于3部，可以补充少量同地区相邻年份或同题材，但绝对不能跨地区乱凑。",
)

AI_WEB_SEARCH_ENABLED = os.environ.get("AI_WEB_SEARCH_ENABLED", "false").lower() in ("1", "true", "yes")
AI_WEB_SEARCH_PROVIDER = os.environ.get("AI_WEB_SEARCH_PROVIDER", "tavily")
AI_WEB_SEARCH_API_KEY = _load_secret_from_file("AI_WEB_SEARCH_API_KEY")
AI_WEB_SEARCH_MAX_RESULTS = int(os.environ.get("AI_WEB_SEARCH_MAX_RESULTS", "3"))

# AI 信息获取策略：
# - "internal_only": 仅使用系统内部数据，禁止任何联网搜索
# - "internal_first": 优先使用系统内部数据，必要时可联网辅助（默认，Windows 生产环境）
# - "web_allowed": 可优先或同时使用联网数据（仅作特殊调试，不推荐用于生产）
AI_INFO_SOURCE_STRATEGY = os.environ.get("AI_INFO_SOURCE_STRATEGY", "internal_first")

HTTP_PROXY = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy") or _load_secret_from_file("HTTP_PROXY") or ""
HTTPS_PROXY = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or _load_secret_from_file("HTTPS_PROXY") or ""
SOCKS_PROXY = (
    os.environ.get("SOCKS_PROXY")
    or os.environ.get("socks_proxy")
    or os.environ.get("ALL_PROXY")
    or os.environ.get("all_proxy")
    or _load_secret_from_file("SOCKS_PROXY")
    or ""
)
NO_PROXY = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or "127.0.0.1,localhost,192.168.*,10.*"

