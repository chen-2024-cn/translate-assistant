"""
翻译请求文本整理: 段内换行视为排版换行, 空行保留为段落边界。
只处理请求文本, 不改变 UI 原文, 不整理译文或词典释义。
"""
import re

from translator.base import BaseTranslator
from translator.lang_util import detect_script

_PARAGRAPH_BREAK = re.compile(r"(\n[^\S\n]*\n(?:[^\S\n]*\n)*)")
_SOFT_BREAK = re.compile(r"[^\S\n]*\n[^\S\n]*")
_HAN_CHAR = re.compile(r"[㐀-䶿一-鿿]")
_CJK_PUNCTUATION = "，。！？；：、（）【】《》“”‘’"


def _join_lines(paragraph: str) -> str:
    lines = _SOFT_BREAK.split(paragraph.strip())
    joined = lines[0]
    for line in lines[1:]:
        if not line:
            continue
        if not joined:
            joined = line
            continue
        left, right = joined[-1], line[0]
        # 连续汉字不插入空格; 中文标点旁不添加排版空格。
        compact = (_HAN_CHAR.fullmatch(left) and _HAN_CHAR.fullmatch(right)) or (
            left in _CJK_PUNCTUATION or right in _CJK_PUNCTUATION
        )
        joined += ("" if compact else " ") + line
    return joined


def split_paragraphs(text: str) -> list:
    """偶数项为已合并的段落, 奇数项为原有空行分隔符(行尾统一为 LF)。"""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace(" ", "\n").replace(" ", "\n\n")
    parts = _PARAGRAPH_BREAK.split(normalized.strip())
    for i in range(0, len(parts), 2):
        parts[i] = _join_lines(parts[i])
    return parts


class ParagraphTranslator(BaseTranslator):
    """面板与划词的公共包装器: 同段整体翻译, 按空行恢复段落。"""

    def __init__(self, translator: BaseTranslator):
        super().__init__()
        self._translator = translator

    def name(self) -> str:
        return self._translator.name()

    def translate(self, text: str, dest: str = "auto") -> dict:
        parts = split_paragraphs(text)
        # 多段时按全文锁定中英方向, 避免单个技术术语段把方向翻转。
        target = dest
        if len(parts) > 1 and dest == "auto":
            target = "en" if detect_script(text) == "zh" else "zh"
        outputs = []
        result = None
        for i, part in enumerate(parts):
            if i % 2:
                outputs.append(part)
                continue
            if not part:
                continue
            current = self._translator.translate(part, target)
            if result is None:
                result = current
            outputs.append(current["translated"])
        if result is None:
            raise ValueError("请输入需要翻译的文本")
        return {**result, "original": text, "translated": "".join(outputs)}
