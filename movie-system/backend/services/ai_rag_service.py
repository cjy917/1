from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from config import (
    AI_WEB_SEARCH_API_KEY,
    AI_WEB_SEARCH_ENABLED,
    AI_WEB_SEARCH_MAX_RESULTS,
    AI_WEB_SEARCH_PROVIDER,
    AI_INFO_SOURCE_STRATEGY,
    MYSQL_DATABASE,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)
from services.movie_service import (
    _row_to_movie,
    get_movie_by_id,
    get_similar_movies,
    list_movies,
    search_suggest,
    split_pipe,
)
from services.recommendation_service import (
    get_content_similar_movies,
    hybrid_recommendations,
)
from services.country_utils import detect_countries_in_query

INTENT_RECOMMEND_SIMILAR = "recommend_similar"
INTENT_RECOMMEND_PERSONAL = "recommend_personal"
INTENT_RECOMMEND_BY_FILTER = "recommend_by_filter"
INTENT_MOVIE_DETAIL = "movie_detail"
INTENT_RATING_QUERY = "rating_query"
INTENT_NEW_RELEASE = "new_release"
INTENT_TRENDING_BOXOFFICE = "trending_boxoffice"
INTENT_ACTOR_FILMOGRAPHY = "actor_filmography"
INTENT_DIRECTOR_FILMOGRAPHY = "director_filmography"
INTENT_CHITCHAT = "chitchat"

REQUIRE_WEB_SEARCH_INTENTS = {INTENT_NEW_RELEASE, INTENT_TRENDING_BOXOFFICE}

TIME_SENSITIVE_WORDS = [
    "今天",
    "最近",
    "正在",
    "新上映",
    "新出",
    "本周",
    "本月",
    "今年",
    "票房",
    "实时",
    "最新",
    "豆瓣",
    "评分排行",
    "热搜",
]


@dataclass
class RetrievalResult:
    intent: str
    internal_data: dict[str, Any] = field(default_factory=dict)
    web_data: list[dict[str, str]] = field(default_factory=list)
    sources_used: list[str] = field(default_factory=list)
    context_text: str = ""

    def to_prompt_block(self) -> str:
        lines: list[str] = []
        lines.append("【系统内部检索数据 - 仅供推理判断，绝对禁止原样输出】")
        lines.append("重要：以下内容是从数据库中检索到的电影结构化信息，你只能在脑中用于推断电影好坏、是否推荐。")
        lines.append("严格禁止把以下内容直接复制到回答里。必须全部翻译成自然的口语化中文句子再输出。")
        lines.append("特别禁止：原样输出「ID:」「评价人数」「上映年份」「类型」「导演」「主演」「推荐理由」「剧情」这些字段名；")
        lines.append("特别禁止：原样输出分号、冒号分隔符，以及任何数字ID。")
        lines.append("判断规则：评分≥8分=必看经典；≥7.5分=口碑极佳；≥7分=口碑不错；≥6分=褒贬不一；<6分=有争议。")
        lines.append("")

        def _fmt_movie_dict(m: dict[str, Any]) -> str:
            parts: list[str] = []
            title = m.get("title") or m.get("name") or ""
            if title:
                parts.append(f"【电影名】《{title}》")
            mid = m.get("movie_id") or m.get("id")
            if mid is not None:
                parts.append(f"【仅内部使用-ID】{mid}")
            rating = m.get("rating") or m.get("rating_douban_style") or m.get("avg_rating_5star")
            if rating is not None and str(rating):
                parts.append(f"【豆瓣评分】{rating}分")
            rc = m.get("rating_count") or m.get("user_count") or m.get("total_count")
            if rc is not None and str(rc):
                parts.append(f"【评价人数统计】{rc}人")
            year = m.get("release_year")
            if year:
                parts.append(f"【公映年份】{year}年")
            genres = m.get("genres")
            if isinstance(genres, list) and genres:
                type_parts = "/".join(str(g) for g in genres)
                parts.append(f"【题材类型】{type_parts}")
            director = m.get("director") or m.get("directors")
            if isinstance(director, list):
                director = director[0] if director else ""
            if director:
                parts.append(f"【导演姓名】{director}")
            actors = m.get("top_actors") or m.get("actors")
            if isinstance(actors, list) and actors:
                parts.append(f"【主要演员名单】{'、'.join(str(a) for a in actors[:3])}")
            reason = m.get("reason")
            if reason:
                parts.append(f"【推荐理由备注】{reason}")
            summary = m.get("summary") or m.get("summary_50chars")
            if summary:
                parts.append(f"【剧情梗概】{str(summary)[:120]}")
            return "｜".join(p for p in parts if p)

        def _fmt_any(v: Any, depth: int = 0) -> str:
            if depth > 3:
                return ""
            if isinstance(v, dict):
                if "title" in v or "movie_id" in v or "rating" in v:
                    return _fmt_movie_dict(v)
                items = []
                for k, val in v.items():
                    if k in ("summary", "summary_50chars") and isinstance(val, str):
                        items.append(f"{k}:{val[:100]}")
                        continue
                    sub = _fmt_any(val, depth + 1)
                    if sub:
                        items.append(f"{k}：{sub}")
                return "；".join(items)
            if isinstance(v, list):
                pieces = []
                for i, item in enumerate(v[:8], 1):
                    sub = _fmt_any(item, depth + 1)
                    if sub:
                        pieces.append(f"{i}. {sub}")
                return "\n" + "\n".join(pieces) if pieces else ""
            return str(v)

        if self.internal_data:
            lines.append("【系统内部数据（优先级最高，直接引用其中的片名、评分、导演演员等即可，不要复述本段开头的标记）】")
            for key, value in self.internal_data.items():
                label = {
                    "matched_movie": "用户查询到的目标电影",
                    "similar_movies": "相似电影推荐列表",
                    "personal_recommendations": "为用户个性化推荐的电影列表",
                    "filter_results": "按条件筛选出的电影列表",
                    "actor_movies": "该演员参演的电影列表（优先引用，按评分和热度排序，至少列出5部）",
                    "director_movies": "该导演执导的电影列表（优先引用，按评分和热度排序，至少列出5部）",
                    "fallback_popular": "系统热门电影参考（仅在没有更匹配数据时引用）",
                    "user_rating_stats_in_system": "用户评分统计",
                    "system_latest_available": "系统内最新的电影",
                }.get(key, key)
                formatted = _fmt_any(value)
                if formatted:
                    lines.append(f"【{label}】{formatted}")
        if self.web_data:
            lines.append("【联网搜索补充数据（仅当系统内部数据完全没有对应信息时才参考）】")
            for idx, item in enumerate(self.web_data, 1):
                title = item.get("title", "")
                content = item.get("content", "")
                if content and len(content) > 180:
                    content = content[:180] + "..."
                lines.append(f"{idx}. {title}：{content}")
        return "\n".join(lines)


_INTENT_RULES: list[tuple[str, list[str]]] = [
    (INTENT_RECOMMEND_SIMILAR, ["类似", "相似", "同类型", "像", "一样", "再来", "还有什么"]),
    (INTENT_RATING_QUERY, ["评分", "多少分", "打分", "评价", "口碑", "评分人数", "IMDb"]),
    # F3 张艺谋导演查询修复：补充用户最常用的口语化句式「X拍了哪些电影？」「X演过哪些电影？」
    #   之前只有"拍过的/演过什么/演过的电影"，漏掉"拍了哪些/演过哪些/拍了什么/拍过哪些/有什么作品"等高频问法，
    #   导致意图识别误判为 recommend_similar，走热门电影兜底，出现"张艺谋→哪吒之魔童降世"的错误推荐
    (INTENT_ACTOR_FILMOGRAPHY, [
        "演过什么", "演过哪些", "演过的电影", "出演", "出演过", "主演了", "主演过",
        "参演的", "参演过", "拍过什么", "拍过哪些", "拍了什么", "拍了哪些",
        "演的电影", "演过的片", "主演的", "主演的电影", "作品", "演的作品",
        "电影作品", "演过的作品", "都演过什么", "都演过哪些",
    ]),
    (INTENT_DIRECTOR_FILMOGRAPHY, [
        "导演过什么", "导演过哪些", "导演的电影", "导演的作品",
        "执导", "执导过", "执导的电影", "执导的作品",
        "拍过的", "拍过什么", "拍过哪些", "拍了哪些", "拍了什么", "拍的电影", "拍的片",
        "导过的", "导过什么", "导过哪些", "导的电影", "导演作品", "导演作品有",
        "电影作品", "都导演过什么", "都导过什么", "都拍过哪些", "都拍了哪些",
    ]),
    (INTENT_MOVIE_DETAIL, ["简介", "讲的什么", "剧情", "导演", "主演", "演员", "上映时间", "片长", "时长"]),
    (INTENT_NEW_RELEASE, ["新上映", "正在上映", "最近上映", "新出的", "刚上映", "最近有什么"]),
    (INTENT_TRENDING_BOXOFFICE, ["票房", "实时", "热搜", "热门榜", "排行", "排行榜"]),
    # 注：所有"推荐X片""欧美电影""韩国电影"等带过滤条件的问句，命中关键词越多score越高，优先于纯"推荐"的similar
    (INTENT_RECOMMEND_BY_FILTER, [
        # 类型：带「片」字的完整短语（≥3字，每个得2分，比单字类型更容易在冲突中胜出）
        "动作片", "喜剧片", "科幻片", "爱情片", "悬疑片", "恐怖片", "动画片",
        "犯罪片", "惊悚片", "战争片", "纪录片", "剧情片", "奇幻片", "冒险片",
        "灾难片", "音乐片", "歌舞片", "古装片", "武侠片", "历史片",
        # 类型：原单字/两字兼容（得分1）
        "动作", "喜剧", "科幻", "爱情", "悬疑", "恐怖", "动画", "犯罪", "惊悚", "战争",
        "纪录", "剧情", "奇幻", "冒险", "灾难", "音乐", "歌舞", "古装", "武侠", "历史",
        # 年份/时间
        "2024", "2025", "2023", "2022", "2021", "2020", "2019", "年的电影", "今年的", "去年的", "哪一年的",
        # 国家/地区（长度≥3的得2分，比单独"推荐"得1分更优先）
        "韩国电影", "韩国片", "韩国悬疑", "韩剧电影",
        "日本电影", "日本片", "日影", "日本动画",
        "欧美电影", "欧美大片", "欧美片", "欧美悬疑", "欧美科幻", "欧美动作",
        "好莱坞电影", "好莱坞大片", "好莱坞",
        "国产电影", "国产片", "国产", "内地电影", "内地片",
        "华语电影", "华语片", "中文电影",
        "香港电影", "港片", "香港",
        "台湾电影", "台片", "台湾",
        "泰国电影", "泰国片", "泰剧电影", "泰国恐怖",
        "印度电影", "印度片", "宝莱坞",
        "法国电影", "法国片", "德国电影", "英国电影", "意大利电影", "西班牙电影",
        "欧洲电影", "北欧电影", "日韩电影", "东南亚电影", "北美电影",
    ]),
    (INTENT_RECOMMEND_PERSONAL, ["给我推荐", "为我推荐", "个性化", "我喜欢的", "猜我喜欢"]),
]


def _get_mysql_conn():
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=DictCursor,
    )


def detect_intent(text: str, history: list[dict[str, Any]] | None = None) -> str:
    text = text.strip()
    if not text:
        return INTENT_CHITCHAT
    text_lower = text
    last_assistant_mentions_movie = False
    if history:
        for h in reversed(history[-4:]):
            if h.get("role") == "user":
                break
            if h.get("role") == "assistant" and isinstance(h.get("content"), str):
                if "《" in h["content"] and "电影" in h["content"]:
                    last_assistant_mentions_movie = True
                    break
    if last_assistant_mentions_movie and re.match(r"^(推荐|好的|嗯|行|可以|再来几部|类似的|一样的|好看的)$", text):
        return INTENT_RECOMMEND_SIMILAR
    hit_scores: dict[str, int] = {}
    for intent, keywords in _INTENT_RULES:
        score = 0
        for kw in keywords:
            if kw in text_lower:
                score += 2 if len(kw) >= 3 else 1
        if score > 0:
            hit_scores[intent] = score
    # ── 关键修复：推荐词 + 过滤词（类型/国家/年份）同时出现 → recommend_by_filter额外加2分，保证在与"给我推荐"的recommend_personal冲突中胜出
    #    用户说"给我推荐五部恐怖片"时，「给我推荐」（2分，personal） vs 「恐怖片 + 推荐boost」（2+2=4分，by_filter） → by_filter胜出
    has_recommend_word = bool(re.search(r"推荐|推几部|推点|来点|找些|找几部|找一下|有什么好", text_lower))
    filter_hit_keywords: list[str] = []
    for kw_list in [
        _INTENT_RULES[[i for i, r in enumerate(_INTENT_RULES) if r[0] == INTENT_RECOMMEND_BY_FILTER][0]][1],
    ]:
        for kw in kw_list:
            if kw in text_lower:
                filter_hit_keywords.append(kw)
    has_filter_word = len(filter_hit_keywords) >= 1
    if has_recommend_word and has_filter_word and INTENT_RECOMMEND_BY_FILTER in hit_scores:
        hit_scores[INTENT_RECOMMEND_BY_FILTER] += 2  # boost: 强力让带过滤的推荐走BY_FILTER路径（DB查具体genre/country/year）
    if not hit_scores:
        if re.match(r"^[你您好嗨在吗在不？?。!\s！\.]+$", text):
            return INTENT_CHITCHAT
        return INTENT_RECOMMEND_SIMILAR if any(ch in text for ch in "影电推") else INTENT_CHITCHAT
    return max(hit_scores.items(), key=lambda kv: kv[1])[0]


def _extract_movie_title(text: str, history: list[dict[str, Any]] | None = None) -> str:
    m = re.search(r"《([^》]+)》", text)
    if m:
        return m.group(1).strip()
    for suffix in ["这部电影", "这个片", "这部片", "这部"]:
        if suffix in text and history:
            for h in reversed(history[-8:]):
                if not isinstance(h.get("content"), str):
                    continue
                mh = re.search(r"《([^》]+)》", h["content"])
                if mh:
                    return mh.group(1).strip()
    cleaned = re.sub(r"[，。！？、：；（）《》\s,?!:;()]+", " ", text).strip()
    for stop in ["推荐", "类似", "相似", "同类型", "一样", "评分", "多少", "简介", "剧情"]:
        cleaned = cleaned.replace(stop, " ")
    cleaned = cleaned.strip()
    if len(cleaned) <= 20 and len(cleaned) >= 1:
        return cleaned
    return ""


def _extract_year(text: str) -> int | None:
    # 仅允许 1950~2027 范围内的真实年份（明年之后的远期未来年份绝不匹配，避免LLM幻觉）
    m = re.search(r"(19[5-9]\d|20[0-2]\d)", text)
    if m:
        y = int(m.group(1))
        if 1950 <= y <= 2027:
            return y
    return None


def _extract_genre(text: str) -> str | None:
    genres = [
        "动作", "喜剧", "科幻", "爱情", "悬疑", "犯罪", "恐怖", "惊悚",
        "动画", "奇幻", "冒险", "剧情", "战争", "家庭", "音乐", "古装",
        "武侠", "历史", "纪录", "灾难", "歌舞",
    ]
    for g in genres:
        if g in text:
            return g  # 返回不带"片"字，与DB genres存储格式对齐
    return None


# F3 张艺谋导演查询修复（二）：人名提取的后缀白名单。必须先strip标点再匹配后缀（"拍了哪些电影?"里的"?"会破坏直接in判断）。
#   重要：后缀按"从长到短"排序，"拍了哪些电影"必须在"的电影"之前被匹配并剥离，否则只剥离"的电影"剩"张艺谋拍了哪些"→长度>6→提取不到"张艺谋"
_PEOPLE_QUERY_SUFFIXES = [
    # 最长5-7字明确意图的句式（优先匹配）
    "导演过哪些电影作品", "导演过什么电影作品", "导过什么电影作品", "导过哪些电影作品",
    "都导演过什么电影", "都导过什么电影", "都拍过哪些电影", "都拍了哪些电影",
    "导演过什么电影", "导演过哪些电影", "导过什么电影", "导过哪些电影",
    "拍了哪些电影作品", "拍了什么电影作品", "拍过哪些电影作品", "拍过什么电影作品",
    "拍了哪些电影", "拍了什么电影", "拍过哪些电影", "拍过什么电影", "拍过的电影有哪些",
    "演过哪些电影作品", "演过什么电影作品", "演过的电影作品有哪些",
    "演过哪些电影", "演过什么电影", "演过的电影有哪些", "演的电影有哪些",
    "演过哪些片", "演过什么片", "演的哪些片", "主演过哪些电影", "主演过什么电影",
    "演过什么电影", "演过的电影", "出演过什么", "出演过哪些", "主演了哪些电影", "主演的电影",
    "参演的电影", "演的电影",
    "作品有哪些", "有哪些作品", "都有什么作品", "都有哪些作品",
    # 短后缀（兜底）
    "的电影", "演过", "主演的", "导演作品", "拍过的", "拍了哪些", "拍过哪些",
    "拍了什么", "拍过什么", "演过哪些", "演过什么", "演过的",
    "导过的", "执导的", "导演的", "导演过的",
]


def _extract_person_name(text: str, intent: str) -> str:
    """从问句中提取人名。例如'吴京演过什么电影' -> '吴京'

    F3 张艺谋导演修复：先去掉标点符号再做后缀匹配（用户问句末尾'？/！'等会让'suffix in cleaned'直接失败）。
    匹配不到后缀时，兜底直接取第一个长度∈[2,6]的连续中文字符串，避免常见人名漏提取。
    """
    cleaned = text.strip()
    # F3 预清理：剥离问句尾部/中间的标点符号（用户常带"？！。，"），与suffix比较前必须做
    punctuation_free = re.sub(r"[，。！？、：；（）《》「」『』·,\.!?:;()\s]+", " ", cleaned).strip()
    # 优先用"无标点版本"匹配长后缀；如果命中后缀在punctuation_free的位置，就对应在cleaned上剥离
    matched_suffix = None
    for suf in _PEOPLE_QUERY_SUFFIXES:
        if suf and suf in punctuation_free:
            matched_suffix = suf
            break
    if matched_suffix:
        # 找到punctuation_free里matched_suffix起始位置之前的内容；在cleaned上按相同策略去掉最后一次出现
        # 简化方案：直接在punctuation_free上截取前缀（已经去掉了空格/标点，人名也在）
        punctuation_clean_stripped = punctuation_free
        # 如果suffix出现在punctuation_free末尾（更常见），直接endswith处理；否则按rfind去掉最右一次出现
        if punctuation_clean_stripped.endswith(matched_suffix):
            punctuation_clean_stripped = punctuation_clean_stripped[:len(punctuation_clean_stripped) - len(matched_suffix)]
        else:
            idx = punctuation_clean_stripped.rfind(matched_suffix)
            if idx >= 0:
                punctuation_clean_stripped = punctuation_clean_stripped[:idx]
        punctuation_free = punctuation_clean_stripped.strip()

    cleaned = punctuation_free

    for prefix in ["我想问一下", "请问", "说说", "介绍", "查一下", "查询", "找"]:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
    for stop_word in ["的", "是", "有", "和", "与", "跟", "同"]:
        cleaned = cleaned.replace(stop_word, " ")
    cleaned = " ".join(cleaned.split())
    if 2 <= len(cleaned) <= 6:
        return cleaned
    tokens = cleaned.split()
    for t in tokens:
        if 2 <= len(t) <= 6:
            return t
    # F3 兜底：如果上面的逻辑全丢了（最常见的情况：后缀完全不在白名单里），
    #   就从原始清理后的字符串里，按顺序取第一个长度2-6的连续汉字片段当人名。
    #   注意只允许"纯中文汉字/·"（兼容"·"如复姓/翻译名），避免匹配到数字等。
    m = re.search(r"[\u4e00-\u9fff·]{2,6}", text)
    if m:
        candidate = m.group(0)
        # 过滤掉显然是电影/通用词的片段（虽然很少发生在意图已确认是作品查询时）
        blacklist = {"电影", "作品", "导演", "演员", "主演", "评分", "排行", "票房", "最近", "好看", "推荐"}
        if candidate not in blacklist:
            return candidate
    return ""


def _query_db_movie_stats(movie_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not movie_ids:
        return {}
    placeholders = ",".join(["%s"] * len(movie_ids))
    try:
        with _get_mysql_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT movie_id,
                           AVG(score) AS avg_score,
                           COUNT(*) AS total_count,
                           COUNT(DISTINCT user_id) AS user_count
                    FROM user_ratings
                    WHERE movie_id IN ({placeholders})
                    GROUP BY movie_id
                    """,
                    tuple(movie_ids),
                )
                rows = cursor.fetchall()
    except Exception:
        return {}
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        mid = int(row["movie_id"])
        avg = float(row["avg_score"]) if row["avg_score"] is not None else 0.0
        result[mid] = {
            "movie_id": mid,
            "avg_rating_5star": round(avg, 2),
            "rating_count": int(row["total_count"] or 0),
            "user_count": int(row["user_count"] or 0),
        }
    return result


def _search_movie_by_title(title: str, limit: int = 3) -> list[dict[str, Any]]:
    if not title:
        return []
    direct = search_suggest(title, limit=limit)
    if direct:
        result = []
        for d in direct:
            mid = int(d.get("movie_id") or d.get("id") or 0)
            full = get_movie_by_id(mid) if mid else None
            if full:
                result.append(full)
        if result:
            return result
    listed = list_movies(keyword=title, page_size=limit, sort="popular")
    return listed.get("items", [])


def _summarize_movies(movies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summarized = []
    for m in movies:
        summarized.append(
            {
                "movie_id": m.get("movie_id") or m.get("id"),
                "title": m.get("title"),
                "rating_douban_style": m.get("rating"),
                "rating_count": m.get("rating_count"),
                "release_year": m.get("release_year"),
                "genres": split_pipe(m.get("genres")),
                "countries": split_pipe(m.get("countries")),
                "director": (split_pipe(m.get("directors")) or [""])[0],
                "top_actors": split_pipe(m.get("actors"))[:3],
                "summary_50chars": (m.get("summary") or "")[:80],
            }
        )
    return summarized


def retrieve_internal_data(intent: str, text: str, user_id: int | None = None, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {}
    title = _extract_movie_title(text, history)
    year = _extract_year(text)
    genre = _extract_genre(text)
    countries = detect_countries_in_query(text)  # 地区过滤：欧美/韩国/华语/日本等
    has_filter = bool(year or genre or countries)
    if intent in (INTENT_RECOMMEND_SIMILAR, INTENT_MOVIE_DETAIL, INTENT_RATING_QUERY):
        if title:
            found = _search_movie_by_title(title, limit=1)
            if found:
                anchor = found[0]
                mid = int(anchor.get("movie_id") or anchor.get("id") or 0)
                data["matched_movie"] = {
                    "movie_id": mid,
                    "title": anchor.get("title"),
                    "rating": anchor.get("rating"),
                    "rating_count": anchor.get("rating_count"),
                    "genres": split_pipe(anchor.get("genres")),
                    "directors": split_pipe(anchor.get("directors")),
                    "actors": split_pipe(anchor.get("actors"))[:5],
                    "release_year": anchor.get("release_year"),
                    "summary": (anchor.get("summary") or "")[:200],
                    "countries": split_pipe(anchor.get("countries")),
                    "duration": anchor.get("duration"),
                }
                stats = _query_db_movie_stats([mid])
                if mid in stats:
                    data["matched_movie"]["user_rating_stats_in_system"] = stats[mid]
                if intent == INTENT_RECOMMEND_SIMILAR:
                    try:
                        sim = get_content_similar_movies(mid, limit=6)
                    except Exception:
                        sim = get_similar_movies(mid, limit=6)
                    if sim:
                        sim_ids = [int(s.get("movie_id") or s.get("id") or 0) for s in sim if s.get("movie_id") or s.get("id")]
                        sim_stats = _query_db_movie_stats(sim_ids)
                        data["similar_movies"] = []
                        for s in sim:
                            smid = int(s.get("movie_id") or s.get("id") or 0)
                            info = {
                                "movie_id": smid,
                                "title": s.get("title"),
                                "rating": s.get("rating"),
                                "reason": s.get("reason") or "内容相似",
                            }
                            if smid in sim_stats:
                                info["user_stats"] = sim_stats[smid]
                            data["similar_movies"].append(info)
                if intent == INTENT_RATING_QUERY:
                    data["rating_query_note"] = "请同时引用系统用户评分(user_rating_stats_in_system)和基础评分(rating)"
        elif intent == INTENT_RECOMMEND_SIMILAR and has_filter:
            # ↓ 关键修复：similar意图但没有锚定电影，只是"韩国电影推荐"这种带过滤的 → 直接按条件过滤，避免返回全球热门
            try:
                filtered = list_movies(
                    page_size=8, sort="popular",
                    year=year, genres=[genre] if genre else None, countries=countries or None,
                )
                data["filter_condition"] = {"year": year, "genre": genre, "countries": countries, "keyword": None}
                data["filter_results"] = _summarize_movies(filtered.get("items", []))
            except Exception as e:
                data["filter_error"] = str(e)
    elif intent == INTENT_RECOMMEND_PERSONAL and user_id:
        try:
            hybrid = hybrid_recommendations(user_id, limit=8)
            recs = hybrid.get("items", []) if isinstance(hybrid, dict) else hybrid
            data["personal_recommendations"] = recs
            data["user_id"] = user_id
        except Exception as e:
            data["personal_error"] = str(e)
        # ── 关键修复：即便是recommend_personal意图，只要有 genre/year/countries 过滤词，也必须走DB带过滤查询补充filter_results
        #    防止用户问「给我推荐恐怖片」时仍只返回纯个性化结果或fallback热门（零信息）导致上下文全是污染旧片名
        if has_filter or (not data.get("personal_recommendations")):
            try:
                filtered = list_movies(
                    page_size=8, sort="popular",
                    year=year, genres=[genre] if genre else None, countries=countries or None,
                )
                data["filter_condition"] = {"year": year, "genre": genre, "countries": countries, "keyword": None}
                data["filter_results"] = _summarize_movies(filtered.get("items", []))
            except Exception as e:
                data["filter_error"] = str(e)
    elif intent == INTENT_RECOMMEND_BY_FILTER:
        params: dict[str, Any] = {"page_size": 8, "sort": "popular"}
        if year:
            params["year"] = year
        if genre:
            params["genres"] = [genre]
        if countries:
            params["countries"] = countries
        if title and not (year or genre or countries):
            params["keyword"] = title
        try:
            filtered = list_movies(**params)
            data["filter_condition"] = {"year": year, "genre": genre, "countries": countries, "keyword": title}
            data["filter_results"] = _summarize_movies(filtered.get("items", []))
        except Exception as e:
            data["filter_error"] = str(e)
    elif intent in (INTENT_ACTOR_FILMOGRAPHY, INTENT_DIRECTOR_FILMOGRAPHY):
        person = _extract_person_name(text, intent)
        if person:
            data["queried_person"] = person
            try:
                # 扩大page_size到30，给"profession概率推断"足够样本。
                # 常见导演也会有演员作品（如张艺谋、周星驰、姜文），仅看前15条容易偏判。
                probe_size = 30
                filtered = list_movies(keyword=person, page_size=probe_size, sort="popular")
                items = filtered.get("items", [])
                if items:
                    # ── F3 张艺谋导演修复（三）：职业概率推断，纠正 detect_intent 的 tie-break 误判 ──
                    # 逻辑：对关键词返回的前 N 条电影，统计 person 在 actors vs directors 列出现次数。
                    #   如果 count_director 明显占优，且用户意图是（歧义导致的）actor_filmography，则自动改成 director_filmography。
                    #   反之，如果 count_actor 明显占优但意图是 director_filmography，则改成 actor。
                    #   这样即使"张艺谋拍了哪些电影"因关键词 tie 被判 actor_filmography，也能在看了数据后改回导演作品查询。
                    cnt_actor, cnt_director, cnt_either = 0, 0, 0
                    for m in items:
                        m_actors = split_pipe(m.get("actors") or "")
                        m_directors = split_pipe(m.get("directors") or "")
                        is_actor = any(person in a for a in m_actors)
                        is_director = any(person in d for d in m_directors)
                        if is_actor:
                            cnt_actor += 1
                        if is_director:
                            cnt_director += 1
                        if is_actor or is_director:
                            cnt_either += 1
                    data["_person_role_debug"] = {
                        "actor_hits": cnt_actor,
                        "director_hits": cnt_director,
                        "either_hits": cnt_either,
                        "intent_before_correction": intent,
                    }
                    corrected_intent = intent
                    # 导演优先判定：cnt_director >= 1 AND cnt_director > cnt_actor → 这个人是导演主导
                    if cnt_director >= 1 and cnt_director > cnt_actor:
                        corrected_intent = INTENT_DIRECTOR_FILMOGRAPHY
                    elif cnt_actor >= 1 and cnt_actor > cnt_director:
                        corrected_intent = INTENT_ACTOR_FILMOGRAPHY
                    # 平局（cnt_director == cnt_actor >= 1）：保留原意图
                    if corrected_intent != intent:
                        data["intent_corrected_from"] = intent
                        intent = corrected_intent

                    key = "actor_movies" if intent == INTENT_ACTOR_FILMOGRAPHY else "director_movies"
                    exact_match: list[dict[str, Any]] = []
                    for m in items:
                        m_actors = split_pipe(m.get("actors") or "")
                        m_directors = split_pipe(m.get("directors") or "")
                        if intent == INTENT_ACTOR_FILMOGRAPHY:
                            ok = any(person in a for a in m_actors)
                        else:
                            ok = any(person in d for d in m_directors)
                        if ok:
                            exact_match.append(m)
                    # F3 修复原 elif bug：之前`elif len(exact_match) < 8 and not ok:` 由于 not ok 恒真，等价于 len<8 就乱塞无关item。
                    #   新逻辑：如果用 corrected intent 精确匹配列（actors/directors）没有结果，
                    #          就 fallback 到"只要这个人出现在演员或导演任一列"就加入，再不行才取 top 关键词兜底。
                    if not exact_match:
                        loose_match: list[dict[str, Any]] = []
                        for m in items:
                            m_actors = split_pipe(m.get("actors") or "")
                            m_directors = split_pipe(m.get("directors") or "")
                            in_any = any(person in a for a in m_actors) or any(person in d for d in m_directors)
                            if in_any:
                                loose_match.append(m)
                            if len(loose_match) >= 10:
                                break
                        exact_match = loose_match or items[:10]
                    # 只保留 top 15 给 LLM，避免超长上下文
                    exact_match = exact_match[:15]
                    movie_ids = [int(m.get("movie_id") or m.get("id") or 0) for m in exact_match if m.get("movie_id") or m.get("id")]
                    stats_map = _query_db_movie_stats(movie_ids)
                    summarized = _summarize_movies(exact_match)
                    for idx, s in enumerate(summarized):
                        mid = s.get("movie_id")
                        if mid and mid in stats_map:
                            st = stats_map[mid]
                            if st.get("avg_rating_5star"):
                                s["rating_douban_style"] = st["avg_rating_5star"]
                            if st.get("user_count"):
                                s["rating_count"] = st["user_count"]
                        movie = exact_match[idx] if idx < len(exact_match) else None
                        if movie:
                            s["reason"] = "主演" if intent == INTENT_ACTOR_FILMOGRAPHY else "导演"
                    data[key] = summarized
                    data["total_available"] = len(summarized)
            except Exception as e:
                data["person_error"] = str(e)
        if not data or (len(data) == 1 and "queried_person" in data):
            # 兜底条件：internal_data 完全没电影数据时，才用热门电影兜底
            #   （注意 queried_person 是已填充的描述性字段，不算"有电影数据"，所以单独有queried_person时也算空）
            try:
                fb_params: dict[str, Any] = {"page_size": 5, "sort": "popular"}
                if year:
                    fb_params["year"] = year
                if genre:
                    fb_params["genres"] = [genre]
                if countries:
                    fb_params["countries"] = countries
                popular = list_movies(**fb_params)
                data["fallback_popular"] = _summarize_movies(popular.get("items", []))
            except Exception:
                pass
        return data
    elif intent in REQUIRE_WEB_SEARCH_INTENTS:
        data["note"] = "系统内部数据库仅到历史影片，若结果为空请参考下方联网搜索数据。"
        try:
            latest = list_movies(page_size=8, sort="latest")
            data["system_latest_available"] = _summarize_movies(latest.get("items", []))
        except Exception as e:
            data["latest_error"] = str(e)
    if not data:
        try:
            # 最后兜底：如果问句中有地区/类型/年份关键词，热门也按条件过滤，避免"韩国电影推荐"最后还出现欧美片
            fb_params: dict[str, Any] = {"page_size": 5, "sort": "popular"}
            if year:
                fb_params["year"] = year
            if genre:
                fb_params["genres"] = [genre]
            if countries:
                fb_params["countries"] = countries
            popular = list_movies(**fb_params)
            data["fallback_popular"] = _summarize_movies(popular.get("items", []))
        except Exception:
            pass
    return data


def _search_tavily(query: str, max_results: int) -> list[dict[str, str]]:
    api_key = AI_WEB_SEARCH_API_KEY
    if not api_key:
        return []
    url = "https://api.tavily.com/search"
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
        "include_raw_content": False,
    }
    from services.http_helper import http_json_request

    data, err = http_json_request(
        url,
        method="POST",
        body=payload,
        headers={"Content-Type": "application/json"},
        timeout=15,
        logger_tag="Tavily",
    )
    if err or not data:
        return []
    results: list[dict[str, str]] = []
    for item in data.get("results", []):
        results.append(
            {
                "title": item.get("title", ""),
                "content": item.get("content", ""),
                "url": item.get("url", ""),
            }
        )
    return results


def _build_web_query(intent: str, text: str) -> str | None:
    if intent == INTENT_NEW_RELEASE:
        year = _extract_year(text) or 2025
        return f"{year}年中国大陆院线上映的新电影列表"
    if intent == INTENT_TRENDING_BOXOFFICE:
        if "豆瓣" in text:
            return "豆瓣电影 实时热门榜 排行榜"
        return "中国电影票房实时排行榜 本周"
    time_hit = any(w in text for w in TIME_SENSITIVE_WORDS)
    if time_hit:
        return f"{text.strip()} 2025 最新信息"
    return None


def retrieve_web_data(intent: str, text: str) -> list[dict[str, str]]:
    if not AI_WEB_SEARCH_ENABLED:
        return []
    query = _build_web_query(intent, text)
    if not query:
        return []
    provider = (AI_WEB_SEARCH_PROVIDER or "tavily").lower()
    try:
        if provider == "tavily":
            return _search_tavily(query, max_results=AI_WEB_SEARCH_MAX_RESULTS)
    except (urllib.error.URLError, urllib.error.HTTPError, Exception):
        return []
    return []


def run_full_rag_pipeline(
    user_message: str,
    history: list[dict[str, Any]] | None = None,
    user_id: int | None = None,
) -> RetrievalResult:
    intent = detect_intent(user_message, history)
    internal = retrieve_internal_data(intent, user_message, user_id=user_id, history=history)
    sources: list[str] = []
    if internal:
        sources.append("system_db")
    web: list[dict[str, str]] = []
    use_web = intent in REQUIRE_WEB_SEARCH_INTENTS or (
        not internal and any(w in user_message for w in TIME_SENSITIVE_WORDS)
    )
    # Respect AI info source strategy from config
    if AI_INFO_SOURCE_STRATEGY == "internal_only":
        use_web = False
    if use_web:
        web = retrieve_web_data(intent, user_message)
        if web:
            sources.append("web_search")
    result = RetrievalResult(
        intent=intent,
        internal_data=internal,
        web_data=web,
        sources_used=sources,
    )
    result.context_text = result.to_prompt_block()
    return result
