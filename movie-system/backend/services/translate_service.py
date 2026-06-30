from deep_translator import GoogleTranslator


def translate_text(text: str, target_lang: str = "zh-CN", source_lang: str = "auto") -> str:
    text = (text or "").strip()
    if not text:
        return ""
    if len(text) > 4500:
        chunks = [text[i : i + 4500] for i in range(0, len(text), 4500)]
        return "\n".join(GoogleTranslator(source=source_lang, target=target_lang).translate(chunk) for chunk in chunks)
    return GoogleTranslator(source=source_lang, target=target_lang).translate(text)
