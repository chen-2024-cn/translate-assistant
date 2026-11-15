"""
Google 翻译引擎 (基于 deep-translator)
免费、无需注册，底层调用 Google Translate API

翻译方向不再依赖 langdetect (纯汉字短文本常被误判为韩语/日语),
改用 Unicode 字符脚本做确定性判断, 并对译文加质量门, 见 translator/lang_util.py
"""
from translator.base import BaseTranslator
from translator.lang_util import detect_script, result_matches_target, is_noop_translation


class GoogleTranslator(BaseTranslator):
    """Google 翻译实现"""

    def name(self) -> str:
        return "Google 翻译"

    def translate(self, text: str, dest: str = "auto") -> dict:
        from deep_translator import GoogleTranslator as GT

        # deep-translator 语言代码映射
        dest_map = {"zh": "zh-CN", "en": "en", "auto": "auto"}

        # 根据目标语言检测源语言
        if dest == "auto":
            script = detect_script(text)
            if script == "zh":
                source, target = "zh-CN", "en"
            elif script == "en":
                source, target = "en", "zh-CN"
            else:
                # 韩/日/未知: 交给 Google 自动识别源语言, 统一翻成中文
                source, target = "auto", "zh-CN"
        else:
            source = "auto"
            target = dest_map.get(dest, dest)

        translator = GT(source=source, target=target)
        translated = translator.translate(text)

        if not translated or not translated.strip():
            raise RuntimeError("Google 翻译返回空结果")
        # 质量门: 目标为英文但译文仍是中文为主 → 视为引擎返回垃圾, 判失败(触发 fallback)
        if not result_matches_target(translated, target):
            raise RuntimeError(f"译文语言与目标不符, 疑似引擎返回垃圾结果: {translated[:50]}")
        # 空翻译门: 中文原文"译成中文"且结果与原文逐字相同 → 方向误判/引擎未翻译, 判失败(触发 fallback)
        if is_noop_translation(text, translated, target):
            raise RuntimeError("译文与原文相同, 引擎未执行翻译")

        return {
            "original": text,
            "translated": translated,
            "source_lang": source,
            "target_lang": target,
        }
