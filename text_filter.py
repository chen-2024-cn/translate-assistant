"""
选中文本过滤
判断选中的内容值不值得翻译 (纯数字/符号、代码片段、路径、标识符等不翻译)
"""
import re

_HAS_WORD = re.compile(r"[A-Za-z一-鿿]")

_PATH_OR_URL = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/[\w.-]+/|https?://|www\.)")

# snake_case / camelCase / PascalCase 单个标识符
_IDENTIFIER = re.compile(
    r"^(?:[A-Za-z]+(?:_[A-Za-z0-9]+)+|[a-z]+(?:[A-Z][a-z0-9]*)+|[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+)$"
)

# 强代码特征: 花括号、箭头、比较/逻辑运算符、空参数调用、下标、行尾分号、标签
_CODE_SYMBOLS = re.compile(
    r"[{}]|=>|->|::|==|!=|&&|\|\||</?\w|\w\(\)|\w\[[^\]\s]*\]|;[ \t]*$",
    re.M,
)


def has_translatable_text(text: str) -> bool:
    """至少包含一个字母或汉字"""
    return bool(_HAS_WORD.search(text))


def looks_like_code(text: str) -> bool:
    s = text.strip()
    if not s:
        return False
    if " " not in s and "\n" not in s:
        if _PATH_OR_URL.match(s) or _IDENTIFIER.match(s):
            return True
    hits = len(_CODE_SYMBOLS.findall(s))
    return hits >= 2 or hits / len(s) > 0.08
