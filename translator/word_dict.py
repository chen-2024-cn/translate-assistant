"""
单词词典查询 — 只对"单词"补充词性与多种词义, 句子不受影响

数据源: 百度翻译词典 sug 接口 (免费, 无需 key, 与百度翻译网页版词典同源)
典型返回: time -> "n. 时间; 次; 时代; 时刻 vt. 为…安排时间; 测定…的时间"

设计原则:
- 句子(含空格/换行/标点、超长中文)一律返回 False, 直通正常机翻, 不发词典请求
- 接口失败/未命中: 静默回退机翻结果, 绝不因词典问题阻断翻译
"""
import re

import requests

_SUG_API = "https://fanyi.baidu.com/sug"
_TIMEOUT = 5

# 英文单词: 字母开头, 允许撇号/连字符, 总长 ≤ 30
_EN_WORD = re.compile(r"^[A-Za-z][A-Za-z'\-]{0,29}$")
# 中文词: 1~6 个纯汉字 (超过 6 字按句子处理, 如事故句"明天预期什么时候"为 8 字)
_ZH_WORD = re.compile(r"^[一-鿿]{1,6}$")
# 词性标签: 用于把整段释义按词性拆行显示
_POS_TAG = re.compile(
    r"\s+(?=(?:vt|vi|adj|adv|prep|conj|pron|abbr|num|int|pl|n|v)\.\s)"
)


def is_single_word(text: str) -> bool:
    """是否单个单词 (英文单词 或 ≤6字中文词); 句子/带标点/混合内容一律 False"""
    s = (text or "").strip()
    if not s or re.search(r"\s", s):
        return False
    return bool(_EN_WORD.match(s) or _ZH_WORD.match(s))


def _format_meaning(v: str) -> str:
    """把整段释义按词性拆行, n./vt./adj. 各占一行, 便于阅读"""
    return _POS_TAG.sub("\n", v.strip())


def lookup_word(word: str):
    """查百度词典, 返回"词性+多词义"字符串; 接口异常或未命中返回 None"""
    try:
        r = requests.post(_SUG_API, data={"kw": word}, timeout=_TIMEOUT,
                          headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        payload = r.json()
        if payload.get("errno") != 0:
            return None
        entries = payload.get("data") or []
        # 优先大小写精确命中, 其次忽略大小写; 其他词头(如 timer/timed)不混入
        hits = [e for e in entries if e.get("k") == word]
        if not hits:
            hits = [e for e in entries
                    if (e.get("k") or "").lower() == word.lower()]
        lines = []
        for e in hits[:2]:
            v = (e.get("v") or "").strip()
            if v:
                lines.append(_format_meaning(v))
        return "\n".join(lines) or None
    except Exception:
        return None


def enrich(text: str, translated: str) -> str:
    """翻译结果增强:
    - 单词且词典命中: 显示词性+多词义, 机翻若提供了增量信息则附在下方作参考
    - 句子 / 词典未命中 / 接口失败: 原样返回机翻结果
    """
    word = (text or "").strip()
    if not is_single_word(word):
        return translated
    meaning = lookup_word(word)
    if not meaning:
        return translated
    mt = (translated or "").strip()
    if mt and mt not in meaning:
        return f"{meaning}\n————\n{mt}"
    return meaning
