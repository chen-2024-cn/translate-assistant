"""引擎层回归测试: 方向选择 + 质量门 + 降级链 (全部 mock 网络, 不发真实请求)"""
import unittest
from unittest import mock

from translator.mymemory import MyMemoryTranslator
from translator.fallback import FallbackTranslator


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self._status = status

    def raise_for_status(self):
        if self._status >= 400:
            raise RuntimeError(f"HTTP {self._status}")

    def json(self):
        return self._payload


def _mymemory_payload(text, status=200):
    return {"responseStatus": status,
            "responseData": {"translatedText": text, "match": 0.85}}


class TestMyMemoryDirection(unittest.TestCase):
    def test_chinese_uses_zh_en_pair(self):
        # 事故回归: 中文必须以 zh-CN|en 请求, 而不是 langdetect 误判出的 ko|zh-CN
        captured = {}

        def fake_get(url, params=None, timeout=None):
            captured.update(params)
            return _FakeResponse(_mymemory_payload("What time do you expect tomorrow?"))

        with mock.patch("translator.mymemory.requests.get", fake_get):
            r = MyMemoryTranslator({}).translate("明天预期什么时候", "auto")

        self.assertEqual(captured["langpair"], "zh-CN|en")
        self.assertEqual(r["translated"], "What time do you expect tomorrow?")


class TestMyMemoryQualityGate(unittest.TestCase):
    def test_garbage_chinese_result_raises(self):
        # 事故回归: 引擎对英文目标返回汉字垃圾 → 必须抛错, 不能展示给用户
        def fake_get(url, params=None, timeout=None):
            return _FakeResponse(_mymemory_payload("时间段为"))

        with mock.patch("translator.mymemory.requests.get", fake_get):
            with self.assertRaises(RuntimeError):
                MyMemoryTranslator({}).translate("明天预期什么时候", "auto")

    def test_api_warning_raises(self):
        def fake_get(url, params=None, timeout=None):
            return _FakeResponse(_mymemory_payload("MYMEMORY WARNING: QUOTA EXCEEDED"))

        with mock.patch("translator.mymemory.requests.get", fake_get):
            with self.assertRaises(RuntimeError):
                MyMemoryTranslator({}).translate("hello", "auto")


class _FakeDeepTranslatorGT:
    """替身 deep_translator.GoogleTranslator: 记录构造参数, 可注入结果/异常"""
    instances = []
    result = "fake translation"
    error = None

    def __init__(self, source=None, target=None):
        self.source, self.target = source, target
        type(self).instances.append(self)

    def translate(self, text):
        if type(self).error:
            raise type(self).error
        return type(self).result


class TestGoogleDirection(unittest.TestCase):
    def setUp(self):
        _FakeDeepTranslatorGT.instances = []
        _FakeDeepTranslatorGT.result = "When do you expect tomorrow"
        _FakeDeepTranslatorGT.error = None

    def test_chinese_detected_as_zh_not_ko(self):
        # 事故回归: langdetect 误判 ko 时旧代码给出 source=auto,target=zh-CN(方向全反)
        from translator.google import GoogleTranslator
        with mock.patch("deep_translator.GoogleTranslator", _FakeDeepTranslatorGT):
            GoogleTranslator({}).translate("明天预期什么时候", "auto")
        gt = _FakeDeepTranslatorGT.instances[-1]
        self.assertEqual(gt.source, "zh-CN")
        self.assertEqual(gt.target, "en")

    def test_english_to_chinese(self):
        from translator.google import GoogleTranslator
        with mock.patch("deep_translator.GoogleTranslator", _FakeDeepTranslatorGT):
            GoogleTranslator({}).translate("hello world", "auto")
        gt = _FakeDeepTranslatorGT.instances[-1]
        self.assertEqual(gt.source, "en")
        self.assertEqual(gt.target, "zh-CN")

    def test_garbage_result_raises(self):
        from translator.google import GoogleTranslator
        _FakeDeepTranslatorGT.result = "时间段为"
        with mock.patch("deep_translator.GoogleTranslator", _FakeDeepTranslatorGT):
            with self.assertRaises(RuntimeError):
                GoogleTranslator({}).translate("明天预期什么时候", "auto")


class _FailingEngine:
    """模拟被限流(429)的 Google 引擎"""
    def name(self):
        return "故障引擎"

    def translate(self, text, dest="auto"):
        raise RuntimeError("429 Too Many Requests")


class TestFallbackChain(unittest.TestCase):
    def test_incident_end_to_end(self):
        # 完整事故链路回归: 主引擎429 → 降级MyMemory → 方向正确zh-CN|en → 正常英文译文
        captured = {}

        def fake_get(url, params=None, timeout=None):
            captured.update(params)
            return _FakeResponse(_mymemory_payload("What time do you expect tomorrow?"))

        fb = FallbackTranslator([_FailingEngine(), MyMemoryTranslator({})])
        with mock.patch("translator.mymemory.requests.get", fake_get):
            r = fb.translate("明天预期什么时候", "auto")

        self.assertEqual(captured["langpair"], "zh-CN|en")
        self.assertEqual(r["translated"], "What time do you expect tomorrow?")
        self.assertEqual(fb.name(), "MyMemory 翻译")


if __name__ == "__main__":
    unittest.main()
