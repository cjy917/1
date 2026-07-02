import re

CANONICAL_COUNTRIES: dict[str, list[str]] = {
    "美国": ["United States of America", "United States", "USA", "US", "美国"],
    "英国": ["United Kingdom", "UK", "英国"],
    "法国": ["France", "法国"],
    "德国": ["Germany", "德国"],
    "意大利": ["Italy", "意大利"],
    "西班牙": ["Spain", "西班牙"],
    "加拿大": ["Canada", "加拿大"],
    "日本": ["Japan", "日本"],
    "韩国": ["South Korea", "Korea", "Republic of Korea", "韩国", "南韩"],
    "中国大陆": ["中国大陆", "中国", "Mainland China", "China", "People's Republic of China"],
    "中国香港": ["中国香港", "香港", "Hong Kong", "Hong Kong SAR"],
    "中国台湾": ["中国台湾", "台湾", "Taiwan"],
    "印度": ["India", "印度"],
    "澳大利亚": ["Australia", "澳大利亚"],
    "比利时": ["Belgium", "比利时"],
    "瑞典": ["Sweden", "瑞典"],
    "荷兰": ["Netherlands", "荷兰"],
    "俄罗斯": ["Russia", "Russian Federation", "俄罗斯"],
    "墨西哥": ["Mexico", "墨西哥"],
    "巴西": ["Brazil", "巴西"],
    "阿根廷": ["Argentina", "阿根廷"],
    "泰国": ["Thailand", "泰国"],
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
