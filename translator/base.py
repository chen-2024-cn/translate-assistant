"""
翻译引擎基类 —— 策略模式
所有翻译 API 实现必须继承此类
"""
from abc import ABC, abstractmethod


class BaseTranslator(ABC):
    """翻译器抽象基类"""

    def __init__(self, config: dict = None):
        self.config = config or {}

    @abstractmethod
    def translate(self, text: str, dest: str = "auto") -> dict:
        """
        翻译文本
        参数:
            text: 待翻译文本
            dest: 目标语言 - "zh" 中文, "en" 英文, "auto" 自动
        返回:
            {"original": str, "translated": str, "source_lang": str, "target_lang": str}
        """
        pass

    @abstractmethod
    def name(self) -> str:
        """返回翻译器名称"""
        pass
