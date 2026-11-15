"""
翻译器工厂 —— 根据配置创建对应的翻译器实例
在此文件中注册新的翻译 API 即可全局使用
"""
from translator.base import BaseTranslator
import config


def _create_primary() -> BaseTranslator:
    if config.TRANSLATOR == "google":
        from translator.google import GoogleTranslator
        return GoogleTranslator(config.GOOGLE_CONFIG)

    elif config.TRANSLATOR == "baidu":
        from translator.baidu import BaiduTranslator
        return BaiduTranslator(config.BAIDU_CONFIG)

    elif config.TRANSLATOR == "youdao":
        from translator.youdao import YoudaoTranslator
        return YoudaoTranslator(config.YOUDAO_CONFIG)

    elif config.TRANSLATOR == "mymemory":
        from translator.mymemory import MyMemoryTranslator
        return MyMemoryTranslator(config.MYMEMORY_CONFIG)

    else:
        raise ValueError(f"未知的翻译器: {config.TRANSLATOR}")


def create_translator() -> BaseTranslator:
    """根据 config.TRANSLATOR 返回翻译器; 开启 FALLBACK_ENABLED 时主引擎失败会自动改用 MyMemory"""
    from translator.text_processing import ParagraphTranslator

    primary = _create_primary()
    if config.FALLBACK_ENABLED and config.TRANSLATOR != "mymemory":
        from translator.fallback import FallbackTranslator
        from translator.mymemory import MyMemoryTranslator
        primary = FallbackTranslator([primary, MyMemoryTranslator(config.MYMEMORY_CONFIG)])
    return ParagraphTranslator(primary)
