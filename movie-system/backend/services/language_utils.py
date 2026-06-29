import re

# 规范中文名 -> 数据库可能出现的别名（用于筛选匹配）
CANONICAL_LANGUAGES: dict[str, list[str]] = {
    "英语": ["English", "en", "英语"],
    "普通话": ["汉语普通话", "普通话", "国语", "华语", "中文", "zh", "汉语"],
    "粤语": ["粤语", "广州话", "廣州話", "广东话"],
    "日语": ["日语", "日本語", "ja"],
    "法语": ["法语", "Français", "fr"],
    "西班牙语": ["西班牙语", "Español", "es"],
    "德语": ["德语", "Deutsch", "de"],
    "韩语": ["韩语", "朝鲜语", "한국어/조선말", "ko"],
    "意大利语": ["意大利语", "Italiano", "it"],
    "俄语": ["俄语", "Pусский", "Русский", "ru"],
    "葡萄牙语": ["葡萄牙语", "Português", "pt"],
    "印地语": ["印地语", "हिन्दी", "hi"],
    "阿拉伯语": ["阿拉伯语", "العربية", "ar"],
    "荷兰语": ["荷兰语", "Nederlands", "nl"],
    "泰语": ["泰语", "ภาษาไทย", "th"],
    "瑞典语": ["瑞典语", "svenska", "sv"],
    "丹麦语": ["丹麦语", "Dansk", "da"],
    "挪威语": ["挪威语", "Norsk", "no"],
    "波兰语": ["波兰语", "Polski", "pl"],
    "土耳其语": ["土耳其语", "Türkçe", "tr"],
    "希伯来语": ["希伯来语", "עברית", "he"],
    "拉丁语": ["拉丁语", "Latin", "la"],
    "波斯语": ["波斯语", "فارسی", "fa"],
    "闽南语": ["闽南语", "台语"],
    "藏语": ["藏语"],
    "无对白": ["No Language", "无对白"],
}

_TOKEN_SPLIT_RE = re.compile(r"[|、,/·]+")

_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canonical, _aliases in CANONICAL_LANGUAGES.items():
    for _alias in _aliases:
        _ALIAS_TO_CANONICAL[_alias.casefold()] = _canonical
    _ALIAS_TO_CANONICAL[_canonical.casefold()] = _canonical


def _normalize_token(token: str) -> str | None:
    cleaned = token.strip()
    if not cleaned:
        return None
    key = cleaned.casefold()
    if key in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[key]
    if cleaned in CANONICAL_LANGUAGES:
        return cleaned
    if re.fullmatch(r"[a-z]{2,3}", key):
        return None
    if re.search(r"[\u4e00-\u9fff]", cleaned):
        return cleaned
    return None


def extract_canonical_languages(languages_field: str | None) -> set[str]:
    if not languages_field:
        return set()
    canonical: set[str] = set()
    for segment in languages_field.split("|"):
        for token in _TOKEN_SPLIT_RE.split(segment):
            name = _normalize_token(token)
            if name:
                canonical.add(name)
    return canonical


def language_match_aliases(canonical: str) -> list[str]:
    if canonical in CANONICAL_LANGUAGES:
        return CANONICAL_LANGUAGES[canonical]
    return [canonical]


def build_language_filter_options(language_rows: list[str], limit: int = 24) -> list[str]:
    counter: dict[str, int] = {}
    for row in language_rows:
        for name in extract_canonical_languages(row):
            counter[name] = counter.get(name, 0) + 1
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [name for name, _ in ranked[:limit]]
