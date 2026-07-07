"""
【详情页 D3b】评论翻译
路由：POST /api/translate → translate_text
链：百度翻译 API → MyMemory 备用 → 内存缓存
"""
import hashlib
import random
import re
from typing import Any

import requests

from config import BAIDU_TRANSLATE_APP_ID, BAIDU_TRANSLATE_SECRET
from services.http_client import external_get

_CACHE: dict[str, dict[str, Any]] = {}
_MAX_LEN = 2000
_CHUNK_LEN = 1800
_DIRECT_SESSION = requests.Session()
_DIRECT_SESSION.trust_env = False

_BAIDU_LANG = {
    "zh": "zh",
    "zh-cn": "zh",
    "zh-CN": "zh",
    "en": "en",
    "auto": "auto",
}

_MYMEMORY_LANG = {
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh-CN": "zh-CN",
    "en": "en",
    "auto": "auto",
}


class TranslationError(Exception):
    pass


def _normalize_lang(code: str | None) -> str:
    if not code:
        return "auto"
    return _MYMEMORY_LANG.get(code.strip(), code.strip())


def detect_target_lang(text: str) -> str:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if cjk >= latin and cjk >= 4:
        return "en"
    return "zh-CN"


def _guess_source_lang(text: str, target: str) -> str:
    if target == "en":
        return "zh-CN"
    if target == "zh-CN":
        return "en"
    return detect_target_lang(text)


def _to_baidu_lang(code: str) -> str:
    return _BAIDU_LANG.get(code, "auto")


def _split_chunks(text: str, max_len: int = _CHUNK_LEN) -> list[str]:
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    current = ""
    for part in re.split(r"(\n+)", text):
        if not part:
            continue
        if len(current) + len(part) <= max_len:
            current += part
            continue
        if current:
            chunks.append(current)
            current = ""
        while len(part) > max_len:
            chunks.append(part[:max_len])
            part = part[max_len:]
        current = part
    if current:
        chunks.append(current)
    return chunks


def _cache_key(text: str, target: str) -> str:
    digest = hashlib.md5(f"{target}|{text}".encode("utf-8")).hexdigest()
    return digest


def _baidu_translate(text: str, source: str, target: str) -> str:
    if not BAIDU_TRANSLATE_APP_ID or not BAIDU_TRANSLATE_SECRET:
        raise TranslationError("未配置百度翻译密钥")

    from_lang = _to_baidu_lang(source)
    to_lang = _to_baidu_lang(target)
    salt = str(random.randint(32768, 65536))
    sign = hashlib.md5(
        f"{BAIDU_TRANSLATE_APP_ID}{text}{salt}{BAIDU_TRANSLATE_SECRET}".encode("utf-8")
    ).hexdigest()

    resp = _DIRECT_SESSION.get(
        "https://fanyi-api.baidu.com/api/trans/vip/translate",
        params={
            "q": text,
            "from": from_lang,
            "to": to_lang,
            "appid": BAIDU_TRANSLATE_APP_ID,
            "salt": salt,
            "sign": sign,
        },
        timeout=12,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("error_code"):
        raise TranslationError(payload.get("error_msg") or "百度翻译服务异常")
    translated = (payload.get("trans_result") or [{}])[0].get("dst", "").strip()
    if not translated:
        raise TranslationError("翻译结果为空")
    return translated


def _mymemory_translate(text: str, source: str, target: str, use_proxy: bool = False) -> str:
    langpair = f"{source}|{target}"
    if source == "auto":
        langpair = f"auto|{target}"
    getter = external_get if use_proxy else _DIRECT_SESSION.get
    resp = getter(
        "https://api.mymemory.translated.net/get",
        params={"q": text, "langpair": langpair},
        timeout=12,
    )
    resp.raise_for_status()
    payload = resp.json()
    status = payload.get("responseStatus")
    if status and int(status) >= 400:
        detail = payload.get("responseDetails") or "翻译服务暂时不可用"
        raise TranslationError(detail)
    translated = (payload.get("responseData") or {}).get("translatedText") or ""
    translated = translated.strip()
    if not translated:
        raise TranslationError("翻译结果为空")
    return translated


def _translate_chunk(text: str, source: str, target: str) -> tuple[str, str]:
    if BAIDU_TRANSLATE_APP_ID and BAIDU_TRANSLATE_SECRET:
        try:
            return _baidu_translate(text, source, target), "baidu"
        except Exception:
            pass

    errors: list[str] = []
    for use_proxy in (False, True):
        try:
            return _mymemory_translate(text, source, target, use_proxy=use_proxy), "fallback"
        except Exception as exc:
            errors.append(str(exc))

    if BAIDU_TRANSLATE_APP_ID and BAIDU_TRANSLATE_SECRET:
        raise TranslationError("百度翻译与备用服务均不可用，请稍后重试")
    raise TranslationError(
        "未配置百度翻译密钥，且备用翻译服务不可用。"
        "请在 secrets.local 中配置 BAIDU_TRANSLATE_APP_ID 与 BAIDU_TRANSLATE_SECRET"
    )


def translate_text(text: str, target: str | None = None) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if not cleaned:
        raise TranslationError("文本为空")
    if len(cleaned) > _MAX_LEN:
        raise TranslationError("文本过长")

    target_lang = _normalize_lang(target) if target else detect_target_lang(cleaned)
    if target_lang == "auto":
        target_lang = detect_target_lang(cleaned)
    source_lang = _guess_source_lang(cleaned, target_lang)

    cache_id = _cache_key(cleaned, target_lang)
    cached = _CACHE.get(cache_id)
    if cached:
        return {**cached, "cached": True}

    parts = _split_chunks(cleaned)
    translated_parts: list[str] = []
    provider = "fallback"
    for part in parts:
        translated, part_provider = _translate_chunk(part, source_lang, target_lang)
        translated_parts.append(translated)
        if part_provider == "baidu":
            provider = "baidu"

    translated = "".join(translated_parts)
    result = {
        "text": cleaned,
        "translated": translated,
        "source": source_lang,
        "target": target_lang,
        "provider": provider,
        "cached": False,
    }
    _CACHE[cache_id] = result
    return result
