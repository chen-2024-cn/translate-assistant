"""英语词库的词头规范化与旧数据只读展示,不修改旧数据库记录。"""
import re

_ENGLISH_WORD = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)*")
_EDGE_PUNCTUATION = " \t\r\n\"'“”‘’.,!?;:，。！？；：()（）[]【】"


def english_word(text: str) -> str:
    """去掉选区边缘标点,内部只允许单词撇号/连字符,句子和中文不作为词头。"""
    word = (text or "").strip(_EDGE_PUNCTUATION).replace("’", "'").replace("‘", "'")
    return word if len(word) <= 60 and _ENGLISH_WORD.fullmatch(word) else ""


def display_entry(entry: dict) -> dict:
    """英文条目显示中文释义;旧中文条目从已有译词取词头,不猜造/联网翻译。"""
    word = english_word(entry["word"])
    if word:
        return {**entry, "display_word": word, "chinese_meaning": entry["meaning"],
                "legacy": False}
    first = re.split(r"[;；\n]", entry["meaning"].strip(), maxsplit=1)[0].strip()
    # 只接受明确的第一个英文译词,不从英文句子随意取首词。
    word = english_word(first)
    return {**entry, "display_word": word, "chinese_meaning": entry["word"],
            "legacy": True}
