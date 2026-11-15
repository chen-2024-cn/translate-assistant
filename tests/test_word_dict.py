"""word_dict 回归测试: 单词识别 + 词典增强 + 失败回退 (全部 mock 网络)"""
import unittest
from unittest import mock

from translator.word_dict import is_single_word, lookup_word, enrich


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def _post_ok(payload):
    def fake_post(*args, **kwargs):
        return _FakeResponse(payload)
    return fake_post


def _post_boom(*args, **kwargs):
    raise RuntimeError("network down")


TIME_PAYLOAD = {"errno": 0, "data": [
    {"k": "time", "v": "n. 时间; 次; 时代; 时刻 vt. 为…安排时间; 测定…的时间"},
    {"k": "Time", "v": "[人名] 泰姆; [电影]时间"},
    {"k": "timer", "v": "n. 定时器; 计时器"},
]}


class TestIsSingleWord(unittest.TestCase):
    def test_english_words(self):
        for w in ("time", "Time", "don't", "well-known", "a"):
            self.assertTrue(is_single_word(w), w)

    def test_chinese_words(self):
        for w in ("时间", "预期", "译", "人工智能"):
            self.assertTrue(is_single_word(w), w)

    def test_sentences_rejected(self):
        for s in ("明天预期什么时候",        # 事故句回归: 8 字必须按句子处理
                  "hello world", "time is money",
                  "这是一个很长的中文词语",
                  "123", "time!", "   "):
            self.assertFalse(is_single_word(s), s)


class TestLookupWord(unittest.TestCase):
    def test_exact_match_preferred(self):
        with mock.patch("translator.word_dict.requests.post", _post_ok(TIME_PAYLOAD)):
            m = lookup_word("time")
        self.assertIn("n. 时间", m)
        self.assertNotIn("定时器", m)      # 其他词头(timer)不得混入
        self.assertNotIn("泰姆", m)        # 大小写精确命中优先于 Time 条目

    def test_pos_split_lines(self):
        with mock.patch("translator.word_dict.requests.post", _post_ok(TIME_PAYLOAD)):
            m = lookup_word("time")
        self.assertIn("\nvt.", m)          # n. 与 vt. 释义分行显示

    def test_case_insensitive_fallback(self):
        payload = {"errno": 0, "data": [{"k": "Time", "v": "[人名] 泰姆"}]}
        with mock.patch("translator.word_dict.requests.post", _post_ok(payload)):
            self.assertIn("泰姆", lookup_word("time"))

    def test_no_match_returns_none(self):
        with mock.patch("translator.word_dict.requests.post", _post_ok(TIME_PAYLOAD)):
            self.assertIsNone(lookup_word("xyzzy"))

    def test_network_error_returns_none(self):
        with mock.patch("translator.word_dict.requests.post", _post_boom):
            self.assertIsNone(lookup_word("time"))


class TestEnrich(unittest.TestCase):
    def test_sentence_passthrough_without_network(self):
        # 句子: 不允许发起任何词典请求, 机翻结果原样返回
        with mock.patch("translator.word_dict.requests.post", _post_boom):
            self.assertEqual(enrich("明天预期什么时候", "When do you expect tomorrow"),
                             "When do you expect tomorrow")

    def test_word_enriched_with_pos(self):
        with mock.patch("translator.word_dict.requests.post", _post_ok(TIME_PAYLOAD)):
            out = enrich("time", "时间")
        self.assertIn("n. 时间", out)
        self.assertIn("vt.", out)
        self.assertNotIn("————", out)     # 机译"时间"已包含在释义中, 不重复附加

    def test_word_mt_appended_when_extra_info(self):
        payload = {"errno": 0, "data": [{"k": "time", "v": "n. 时光"}]}
        with mock.patch("translator.word_dict.requests.post", _post_ok(payload)):
            out = enrich("time", "时间")
        self.assertIn("n. 时光", out)
        self.assertIn("————", out)        # 机译提供了释义之外的信息 → 附加
        self.assertIn("时间", out.split("————")[1])

    def test_word_lookup_fail_falls_back_to_mt(self):
        with mock.patch("translator.word_dict.requests.post", _post_boom):
            self.assertEqual(enrich("time", "时间"), "时间")


if __name__ == "__main__":
    unittest.main()
