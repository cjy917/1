from __future__ import annotations

import re

CANONICAL_COUNTRIES: dict[str, list[str]] = {
    "美国": ["United States of America", "United States", "USA", "US", "美国", "美"],
    "英国": ["United Kingdom", "UK", "英国", "英"],
    "法国": ["France", "法国", "法"],
    "德国": ["Germany", "德国", "德"],
    "意大利": ["Italy", "意大利", "意"],
    "西班牙": ["Spain", "西班牙", "西"],
    "加拿大": ["Canada", "加拿大", "加"],
    "日本": ["Japan", "日本", "日"],
    "韩国": ["South Korea", "Korea", "Republic of Korea", "韩国", "南韩", "韩"],
    "中国大陆": ["中国大陆", "中国", "Mainland China", "China", "People's Republic of China"],
    "中国香港": ["中国香港", "香港", "Hong Kong", "Hong Kong SAR"],
    "中国台湾": ["中国台湾", "台湾", "Taiwan"],
    "印度": ["India", "印度"],
    "澳大利亚": ["Australia", "澳大利亚", "澳"],
    "比利时": ["Belgium", "比利时"],
    "瑞典": ["Sweden", "瑞典", "瑞"],
    "荷兰": ["Netherlands", "荷兰", "荷"],
    "俄罗斯": ["Russia", "Russian Federation", "俄罗斯", "俄"],
    "墨西哥": ["Mexico", "墨西哥"],
    "巴西": ["Brazil", "巴西"],
    "阿根廷": ["Argentina", "阿根廷"],
    "泰国": ["Thailand", "泰国", "泰"],
    "新加坡": ["Singapore", "新加坡"],
    "爱尔兰": ["Ireland", "爱尔兰"],
    "波兰": ["Poland", "波兰"],
    "丹麦": ["Denmark", "丹麦"],
    "挪威": ["Norway", "挪威"],
    "芬兰": ["Finland", "芬兰"],
    "瑞士": ["Switzerland", "瑞士"],
    "奥地利": ["Austria", "奥地利"],
    "新西兰": ["New Zealand", "新西兰"],
    "菲律宾": ["Philippines", "菲律宾"],
    "马来西亚": ["Malaysia", "马来西亚"],
    "越南": ["Vietnam", "越南"],
    "土耳其": ["Turkey", "土耳其"],
    "以色列": ["Israel", "以色列"],
    "南非": ["South Africa", "南非"],
    "捷克": ["Czech Republic", "Czechia", "捷克"],
    "匈牙利": ["Hungary", "匈牙利"],
    "葡萄牙": ["Portugal", "葡萄牙"],
    "希腊": ["Greece", "希腊"],
    "冰岛": ["Iceland", "冰岛"],
    "卢森堡": ["Luxembourg", "卢森堡"],
}

# 区域/文化聚合 → 展开为 CANONICAL_COUNTRIES 中存在的 canonical 国家名列表
REGION_ALIASES: dict[str, list[str]] = {
    # 用户常说的「欧美电影」= 北美 + 西欧 + 澳新（用户语义下的广义西方/英语+西欧文化圈）
    "欧美": [
        "美国", "英国", "法国", "德国", "意大利", "西班牙", "加拿大", "澳大利亚",
        "爱尔兰", "比利时", "荷兰", "瑞士", "瑞典", "挪威", "丹麦", "芬兰",
        "奥地利", "葡萄牙", "希腊", "冰岛", "卢森堡", "波兰", "捷克",
        "匈牙利", "新西兰",
    ],
    # 「西方」「好莱坞」同欧美
    "西方": [
        "美国", "英国", "法国", "德国", "意大利", "西班牙", "加拿大", "澳大利亚",
        "爱尔兰", "比利时", "荷兰", "瑞士", "瑞典", "挪威", "丹麦", "芬兰",
        "奥地利", "葡萄牙", "希腊", "新西兰",
    ],
    "好莱坞": ["美国", "英国", "加拿大", "澳大利亚"],
    # 欧洲
    "欧洲": [
        "英国", "法国", "德国", "意大利", "西班牙", "爱尔兰", "比利时", "荷兰",
        "瑞士", "瑞典", "挪威", "丹麦", "芬兰", "奥地利", "葡萄牙", "希腊",
        "冰岛", "卢森堡", "波兰", "捷克", "匈牙利", "俄罗斯",
    ],
    "西欧": ["英国", "法国", "德国", "爱尔兰", "比利时", "荷兰", "瑞士", "奥地利", "卢森堡"],
    "北欧": ["瑞典", "挪威", "丹麦", "芬兰", "冰岛"],
    "南欧": ["意大利", "西班牙", "葡萄牙", "希腊"],
    "东欧": ["俄罗斯", "波兰", "捷克", "匈牙利"],
    # 东亚/华语/日韩
    "华语": ["中国大陆", "中国香港", "中国台湾", "新加坡"],
    "中文": ["中国大陆", "中国香港", "中国台湾", "新加坡"],
    "国产": ["中国大陆"],
    "内地": ["中国大陆"],
    "香港": ["中国香港"],
    "台湾": ["中国台湾"],
    "日韩": ["日本", "韩国"],
    "亚洲": ["日本", "韩国", "中国大陆", "中国香港", "中国台湾", "印度", "泰国", "新加坡", "菲律宾", "马来西亚", "越南", "土耳其", "以色列"],
    "东南亚": ["泰国", "新加坡", "菲律宾", "马来西亚", "越南", "印度尼西亚"],
    "南亚": ["印度"],
    # 其他大洲
    "美洲": ["美国", "加拿大", "墨西哥", "巴西", "阿根廷"],
    "北美": ["美国", "加拿大"],
    "拉美": ["墨西哥", "巴西", "阿根廷"],
    "大洋洲": ["澳大利亚", "新西兰"],
    "非洲": ["南非"],
}

# 把 REGION_ALIASES 的别名和 单字简称 也加进全局 _ALIAS_TO_CANONICAL 逆向索引（展开时会被 expand_region_countries 处理）
_REGION_NAME_KEYS = set(REGION_ALIASES.keys())

_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canonical, _aliases in CANONICAL_COUNTRIES.items():
    for _alias in _aliases:
        _ALIAS_TO_CANONICAL[_alias.casefold()] = _canonical
    _ALIAS_TO_CANONICAL[_canonical.casefold()] = _canonical


def canonical_country(token: str) -> str | None:
    cleaned = token.strip()
    if not cleaned:
        return None
    key = cleaned.casefold()
    if key in _ALIAS_TO_CANONICAL:
        return _ALIAS_TO_CANONICAL[key]
    if cleaned in CANONICAL_COUNTRIES:
        return cleaned
    if re.search(r"[\u4e00-\u9fff]", cleaned):
        return cleaned
    return None


def extract_canonical_countries(countries_field: str | None) -> set[str]:
    if not countries_field:
        return set()
    canonical: set[str] = set()
    for segment in countries_field.split("|"):
        for token in re.split(r"[,、/·]+", segment):
            name = canonical_country(token)
            if name:
                canonical.add(name)
    return canonical


def country_match_aliases(canonical: str) -> list[str]:
    if canonical in CANONICAL_COUNTRIES:
        return CANONICAL_COUNTRIES[canonical]
    return [canonical]


def build_country_filter_options(country_rows: list[str], limit: int = 20) -> list[str]:
    counter: dict[str, int] = {}
    for row in country_rows:
        for name in extract_canonical_countries(row):
            counter[name] = counter.get(name, 0) + 1
    ranked = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [name for name, _ in ranked[:limit]]


def expand_region_to_countries(token: str) -> list[str]:
    """把地区/国家token展开为 canonical 国家列表。
    例：'欧美' -> [美国, 英国, 法国, ...]；'韩国' -> ['韩国']；'韩' -> ['韩国']；不认识返回[]"""
    cleaned = token.strip()
    if not cleaned:
        return []
    # 1. 区域别名（优先级最高，防止'美'先被识别成美国后漏掉"欧美"）
    if cleaned in REGION_ALIASES:
        return list(REGION_ALIASES[cleaned])
    # 2. 单字区域简称（长度==1时尝试在REGION_ALIASES中找）
    # 3. 国名 canonical
    if cleaned in CANONICAL_COUNTRIES:
        return [cleaned]
    # 4. 别名
    key = cleaned.casefold()
    if key in _ALIAS_TO_CANONICAL:
        return [_ALIAS_TO_CANONICAL[key]]
    # 5. 英文别名/其他 - 无匹配
    return []


def detect_countries_in_query(text: str) -> list[str]:
    """从用户查询中扫描地区/国家关键词，返回展开后的canonical国家列表（去重保序）。
    例：'20年欧美电影推荐' -> [美国,英国,法国,...,新西兰]；'韩国电影' -> ['韩国']"""
    if not text:
        return []
    found: list[str] = []
    seen: set[str] = set()

    def _push(items: list[str]) -> None:
        for it in items:
            if it and it not in seen:
                seen.add(it)
                found.append(it)

    # 优先级 A：长token优先匹配（先区域名 > 国家名 > 单字简称，避免"欧美"被"美"先吃）
    # 先把所有候选关键词按长度降序排列后再扫描
    keywords: list[tuple[str, list[str]]] = []
    for region_name, canonicals in REGION_ALIASES.items():
        keywords.append((region_name, canonicals))
    for canon, aliases in CANONICAL_COUNTRIES.items():
        keywords.append((canon, [canon]))
        for a in aliases:
            if len(a) >= 2:  # 单字单独在最后扫描
                keywords.append((a, [canon]))
    keywords.sort(key=lambda kv: -len(kv[0]))  # 长的优先，避免短名先匹配
    for kw, expands in keywords:
        if len(kw) < 2:
            continue
        if kw in text:
            _push(expands)
    # 优先级 B：未匹配长token时，再扫描单字简称（韩/美/日/英 等）
    single_chars = [
        ("韩", ["韩国"]), ("日", ["日本"]), ("美", ["美国"]), ("英", ["英国"]),
        ("法", ["法国"]), ("德", ["德国"]), ("意", ["意大利"]), ("西", ["西班牙"]),
        ("泰", ["泰国"]), ("印", ["印度"]), ("俄", ["俄罗斯"]), ("澳", ["澳大利亚"]),
        ("加", ["加拿大"]), ("荷", ["荷兰"]), ("瑞", ["瑞典"]),
    ]
    for ch, expands in single_chars:
        # 只在文本中明确出现该单字且不是更长关键词的内部字符时才匹配
        if ch in text:
            _push(expands)
    # 去重保序
    return found


def country_all_match_aliases(canonical_countries: list[str]) -> list[str]:
    """给定多个canonical国家名，返回所有别名的并集（用于SQL LIKE OR查询）。
    例：['美国','英国'] -> ['United States of America','USA',...,'UK','英国',...]"""
    aliases_out: list[str] = []
    seen_a: set[str] = set()
    for c in canonical_countries:
        for a in country_match_aliases(c):
            if a and a not in seen_a:
                seen_a.add(a)
                aliases_out.append(a)
    return aliases_out

