"""
TTS 语音朗读模块
使用 Windows SAPI5 COM (win32com), 支持中英文自动切换
Python 3.14 完全兼容，无 pyttsx3 依赖
"""
import threading
import re

import config


class TTSEngine:
    """文字转语音引擎 (线程安全, 单例)"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._voice = None
                    cls._instance._speaking = False
        return cls._instance

    def _get_voice(self):
        """延迟初始化 SAPI 语音"""
        if self._voice is None:
            import win32com.client
            self._voice = win32com.client.Dispatch("SAPI.SpVoice")
            self._voice.Rate = int(-2 + (config.TTS_RATE - 1.0) * 6)
            self._voice.Volume = int(config.TTS_VOLUME * 100)
        return self._voice

    def speak(self, text: str):
        """在后台线程中朗读文本"""
        if not text:
            return
        threading.Thread(target=self._do_speak, args=(text,), daemon=True).start()

    def _do_speak(self, text: str):
        import pythoncom
        pythoncom.CoInitialize()  # COM 线程初始化
        try:
            self._speak_inner(text)
        finally:
            self._speaking = False
            pythoncom.CoUninitialize()

    def _speak_inner(self, text: str):
        voice = self._get_voice()
        self._speaking = True
        try:
            voice_token = self._detect_voice_for_text(text)
            if voice_token:
                voice.Voice = voice_token
            voice.Speak(text, 1)  # 1 = SVSFlagsAsync (非阻塞)
            while voice.Status.RunningState != 1:  # 1 = SRSEDone
                import time
                time.sleep(0.1)
        except Exception:
            pass

    def stop(self):
        """停止朗读"""
        if self._voice:
            try:
                self._voice.Speak("", 3)  # 3 = SVSFPurgeBeforeSpeak
            except Exception:
                pass

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def _detect_voice_for_text(self, text: str):
        """根据文本语言选择合适的 SAPI 语音 token"""
        chinese_chars = len(re.findall(r"[\u4e00-\u9fff]", text))
        english_chars = len(re.findall(r"[a-zA-Z]", text))
        total = chinese_chars + english_chars
        if total == 0:
            return None

        is_chinese = chinese_chars > english_chars

        voice = self._get_voice()
        voices = voice.GetVoices()
        for i in range(voices.Count):
            v = voices.Item(i)
            desc = v.GetDescription().lower()
            if is_chinese:
                if any(kw in desc for kw in ("chinese", "zh", "zh-cn", "hong kong", "simplified")):
                    return v
            else:
                if any(kw in desc for kw in ("english", "en-us", "en-gb", "american", "british")):
                    return v
        return None
