"""
MyMemory 翻译引擎 (免费, 无需注册)
匿名每天约 5000 字符额度, 单次请求最多 500 字符, 长文本按句子切块后分段翻译

翻译方向不再依赖 langdetect (纯汉字短文本常被误判为韩语, 曾导致本引擎以
ko|zh-CN 语言对翻译中文, 返回翻译记忆垃圾片段 "时间段为"),
改用 Unicode 字符脚本做确定性判断, 并对译文加质量门, 见 translator/lang_util.py
"""
import html
import re

import requests

from translator.base import BaseTranslator
from translator.lang_util import lang_pair, result_matches_target, is_noop_translation

_API = "https://api.mymemory.translated.net/get"
_CHUNK = 450


def _split(text: str, limit: int = _CHUNK) -> list:
    parts = re.split(r"(?<=[.!?。！？\n])", text)
    chunks, cur = [], ""
    for p in parts:
        while len(p) > limit:
            if cur:
                chunks.append(cur)
                cur = ""
            chunks.append(p[:limit])
            p = p[limit:]
        if len(cur) + len(p) > limit:
            chunks.append(cur)
            cur = p
        else:
            cur += p
    if cur:
        chunks.append(cur)
    return [c for c in chunks if c.strip()]


class MyMemoryTranslator(BaseTranslator):
    def name(self) -> str:
        return "MyMemory 翻译"

    def translate(self, text: str, dest: str = "auto") -> dict:
        src, target = lang_pair(text)
        if dest != "auto":
            target = {"zh": "zh-CN", "en": "en"}.get(dest, dest)
            if src == target:
                # 全文方向锁定后, 纯英文术语段可能已经是目标语言。
                # MyMemory 不接受相同的源/目标语言, 直接保留该段。
                return {"original": text, "translated": text,
                        "source_lang": src, "target_lang": target}
        email = self.config.get("email")
        out = []
        for chunk in _split(text):
            params = {"q": chunk, "langpair": f"{src}|{target}"}
            if email:
                params["de"] = email
            r = requests.get(_API, params=params, timeout=8)
            r.raise_for_status()
            data = r.json()
            translated = (data.get("responseData") or {}).get("translatedText") or ""
            status = int(data.get("responseStatus") or 0)
            if status != 200 or "MYMEMORY WARNING" in translated:
                raise RuntimeError(translated or f"状态码 {status}")
            out.append(html.unescape(translated))

        result = (" " if target == "en" else "").join(out)
        # 质量门: MyMemory 在错误语言对/记忆库脏数据下会返回垃圾片段, 必须拦截,
        # 判失败后由 FallbackTranslator 继续换引擎或向用户明确报错, 绝不把垃圾当译文展示
        if not result_matches_target(result, target):
            raise RuntimeError(f"译文语言与目标不符, 疑似引擎返回垃圾结果: {result[:50]}")
        # 空翻译门: 中文原文"译成中文"且结果与原文逐字相同 → 方向误判/引擎未翻译, 判失败
        if is_noop_translation(text, result, target):
            raise RuntimeError("译文与原文相同, 引擎未执行翻译")

        return {
            "original": text,
            "translated": result,
            "source_lang": src,
            "target_lang": target,
        }
