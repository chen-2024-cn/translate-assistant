"""百度引擎回归测试 (mock 网络, 不发真实请求)
覆盖: 方向选择(to=auto致命bug回归) / 多行拼接 / 分块限速 / 错误处理 / 质量门
"""
import unittest
from unittest import mock

from translator.baidu import BaiduTranslator

CFG = {"appid": "test-appid", "secret_key": "test-secret",
       "api_url": "https://fake.baidu/api"}


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self._status = status

    def raise_for_status(self):
        if self._status >= 400:
            raise RuntimeError(f"HTTP {self._status}")

    def json(self):
        return self._payload


def _ok_payload(dst_lines):
    return {"logid": 1,
            "trans_result": [{"src": "x", "dst": d} for d in dst_lines]}


class TestBaiduDirection(unittest.TestCase):
    def test_chinese_target_english(self):
        # 事故回归: 旧实现发 to=auto, 百度不支持 auto 目标语言, 配置了 key 也必挂
        captured = {}

        def fake_post(url, data=None, timeout=None):
            captured.update(data)
            return _FakeResponse(_ok_payload(["What time do you expect tomorrow"]))

        with mock.patch("translator.baidu.requests.post", fake_post):
            r = BaiduTranslator(CFG).translate("明天预期什么时候", "auto")

        self.assertEqual(captured["to"], "en")
        self.assertEqual(captured["from"], "auto")
        self.assertEqual(r["translated"], "What time do you expect tomorrow")

    def test_english_target_chinese(self):
        captured = {}

        def fake_post(url, data=None, timeout=None):
            captured.update(data)
            return _FakeResponse(_ok_payload(["你好"]))

        with mock.patch("translator.baidu.requests.post", fake_post):
            BaiduTranslator(CFG).translate("hello world", "auto")

        self.assertEqual(captured["to"], "zh")

    def test_explicit_dest(self):
        captured = {}

        def fake_post(url, data=None, timeout=None):
            captured.update(data)
            return _FakeResponse(_ok_payload(["ok"]))

        with mock.patch("translator.baidu.requests.post", fake_post):
            BaiduTranslator(CFG).translate("任意文本", "en")
        self.assertEqual(captured["to"], "en")


class TestBaiduMultiLine(unittest.TestCase):
    def test_all_lines_joined(self):
        # 事故回归: 旧实现只取 trans_result[0], 多行文本从第二行起丢失
        def fake_post(url, data=None, timeout=None):
            return _FakeResponse(_ok_payload(["第一行", "第二行"]))

        with mock.patch("translator.baidu.requests.post", fake_post):
            r = BaiduTranslator(CFG).translate("line1\nline2", "auto")

        self.assertEqual(r["translated"], "第一行\n第二行")


class TestBaiduChunking(unittest.TestCase):
    def test_long_text_split_with_rate_limit(self):
        # 超过 600 字符必须分块(百度单次 2048 字节限制), 且块间必须 sleep 限速(1 QPS)
        calls = []

        def fake_post(url, data=None, timeout=None):
            calls.append(data)
            return _FakeResponse(_ok_payload(["ok"]))

        long_text = "这是一个很长的中文句子。" * 200  # 2400 字符 → 4 块
        with mock.patch("translator.baidu.requests.post", fake_post), \
                mock.patch("translator.baidu.time.sleep") as fake_sleep:
            BaiduTranslator(CFG).translate(long_text, "auto")

        self.assertGreater(len(calls), 1)
        self.assertEqual(fake_sleep.call_count, len(calls) - 1)
        for c in calls:
            self.assertEqual(c["to"], "en")


class TestBaiduErrors(unittest.TestCase):
    def test_error_code_raises(self):
        def fake_post(url, data=None, timeout=None):
            return _FakeResponse({"error_code": "52003",
                                  "error_msg": "UNAUTHORIZED USER"})

        with mock.patch("translator.baidu.requests.post", fake_post):
            with self.assertRaises(RuntimeError) as cm:
                BaiduTranslator(CFG).translate("你好", "auto")
        self.assertIn("52003", str(cm.exception))

    def test_empty_result_raises(self):
        # 事故回归: 旧实现空结果时把原文当译文静默返回
        def fake_post(url, data=None, timeout=None):
            return _FakeResponse({"trans_result": []})

        with mock.patch("translator.baidu.requests.post", fake_post):
            with self.assertRaises(RuntimeError):
                BaiduTranslator(CFG).translate("你好", "auto")

    def test_garbage_chinese_for_english_target_raises(self):
        def fake_post(url, data=None, timeout=None):
            return _FakeResponse(_ok_payload(["时间段为"]))

        with mock.patch("translator.baidu.requests.post", fake_post):
            with self.assertRaises(RuntimeError):
                BaiduTranslator(CFG).translate("明天预期什么时候", "auto")


class TestBaiduNoopGate(unittest.TestCase):
    def test_noop_zh_result_raises(self):
        # 空翻译门: "译成中文"结果与含汉字的原文逐字相同 → 必须抛错(触发降级),
        # 不得把原文当译文静默展示
        def fake_post(url, data=None, timeout=None):
            return _FakeResponse(_ok_payload(["你好世界"]))

        with mock.patch("translator.baidu.requests.post", fake_post):
            with self.assertRaises(RuntimeError):
                BaiduTranslator(CFG).translate("你好世界", "zh")

    def test_proper_noun_identical_not_noop(self):
        # 专有名词原样输出是合法结果(不含汉字), 不得误伤
        def fake_post(url, data=None, timeout=None):
            return _FakeResponse(_ok_payload(["Python"]))

        with mock.patch("translator.baidu.requests.post", fake_post):
            r = BaiduTranslator(CFG).translate("Python", "zh")
        self.assertEqual(r["translated"], "Python")


if __name__ == "__main__":
    unittest.main()
