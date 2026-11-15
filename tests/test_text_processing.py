"""跨行句子回归: 请求保留上下文, 原文不变, 空行仍分段。网络全部 mock。"""
import hashlib
import unittest
from unittest import mock

from translator.base import BaseTranslator
from translator.text_processing import ParagraphTranslator, split_paragraphs
from translator.baidu import BaiduTranslator
from translator.mymemory import MyMemoryTranslator
from tests.test_baidu import CFG, _FakeResponse, _ok_payload


class RecordingTranslator(BaseTranslator):
    def __init__(self):
        super().__init__()
        self.calls = []

    def name(self):
        return "测试引擎"

    def translate(self, text, dest="auto"):
        self.calls.append((text, dest))
        return {"original": text, "translated": "译文:" + text,
                "source_lang": "auto", "target_lang": dest}


class TestTextProcessing(unittest.TestCase):
    def test_chinese_sentence_joined(self):
        self.assertEqual(split_paragraphs("配好后，PyCharm 的 Terminal 会自动帮你\n激活，右下角也会显示 Python 3.14 (.venv)。"),
                         ["配好后，PyCharm 的 Terminal 会自动帮你激活，右下角也会显示 Python 3.14 (.venv)。"])

    def test_english_words_keep_space(self):
        self.assertEqual(split_paragraphs("The meeting will\nstart tomorrow."),
                         ["The meeting will start tomorrow."])

    def test_crlf_cr_and_indentation(self):
        self.assertEqual(split_paragraphs("The meeting\r\n   will start\rtomorrow."),
                         ["The meeting will start tomorrow."])

    def test_chinese_punctuation(self):
        self.assertEqual(split_paragraphs("你好，\n明天\n见。"), ["你好，明天见。"])

    def test_blank_lines_preserved(self):
        self.assertEqual(split_paragraphs("第一\n段。\n \t\n\n第二\n段。"),
                         ["第一段。", "\n \t\n\n", "第二段。"])

    def test_unicode_line_separators(self):
        self.assertEqual(split_paragraphs("第一 段。 第二段。"),
                         ["第一段。", "\n\n", "第二段。"])

    def test_no_changes_to_inline_spaces_and_terms(self):
        text = "PyCharm 的 Terminal 显示 Python 3.14 (.venv)。"
        self.assertEqual(split_paragraphs(text), [text])

    def test_sentence_is_one_request_and_original_kept(self):
        delegate = RecordingTranslator()
        text = "The meeting will\nstart tomorrow."
        result = ParagraphTranslator(delegate).translate(text)
        self.assertEqual(delegate.calls, [("The meeting will start tomorrow.", "auto")])
        self.assertEqual(result["original"], text)

    def test_paragraphs_keep_full_text_direction(self):
        delegate = RecordingTranslator()
        text = "明天\n开会。\n\nPython"
        result = ParagraphTranslator(delegate).translate(text)
        self.assertEqual(delegate.calls, [("明天开会。", "en"), ("Python", "en")])
        self.assertEqual(result["translated"], "译文:明天开会。\n\n译文:Python")
        self.assertEqual(result["original"], text)

    def test_translated_dictionary_lines_not_normalized(self):
        delegate = RecordingTranslator()
        with mock.patch.object(delegate, "translate", return_value={
            "original": "time", "translated": "n. 时间\nvt. 安排时间",
            "source_lang": "en", "target_lang": "zh"}):
            result = ParagraphTranslator(delegate).translate("time")
        self.assertEqual(result["translated"], "n. 时间\nvt. 安排时间")

    def test_blank_input_rejected_without_network(self):
        delegate = RecordingTranslator()
        with self.assertRaises(ValueError):
            ParagraphTranslator(delegate).translate(" \r\n \t ")
        self.assertFalse(delegate.calls)


class TestFactoryNewlineRequests(unittest.TestCase):
    def test_factory_sends_joined_sentence_and_valid_signature(self):
        from translator.factory import create_translator
        from translator import factory
        calls = []

        def post(url, data=None, **kwargs):
            calls.append(dict(data))
            return _FakeResponse(_ok_payload(["The meeting will start tomorrow."]))

        original = "会议将于\r\n明天开始。"
        with mock.patch.object(factory, "_create_primary", return_value=BaiduTranslator(CFG)), \
                mock.patch.object(factory.config, "FALLBACK_ENABLED", False), \
                mock.patch("translator.baidu.requests.post", side_effect=post):
            translator = create_translator()
            result = translator.translate(original)
        self.assertEqual(len(calls), 1)
        request = calls[0]
        self.assertEqual(request["q"], "会议将于明天开始。")
        self.assertEqual(request["to"], "en")
        expected_sign = hashlib.md5((CFG["appid"] + request["q"] + request["salt"] + CFG["secret_key"]).encode()).hexdigest()
        self.assertEqual(request["sign"], expected_sign)
        self.assertEqual(result["original"], original)
        self.assertEqual(translator.name(), "百度翻译")

    def test_fallback_gets_joined_sentence(self):
        from translator.fallback import FallbackTranslator
        primary = RecordingTranslator()
        requests = []

        def get(url, params=None, **kwargs):
            requests.append(dict(params))
            return _FakeResponse({"responseStatus": 200, "responseData": {
                "translatedText": "The meeting will start tomorrow."}})

        with mock.patch.object(primary, "translate", side_effect=RuntimeError("network down")), \
                mock.patch("translator.mymemory.requests.get", side_effect=get), \
                mock.patch("translator.fallback._failed_at", {}):
            translator = ParagraphTranslator(FallbackTranslator([primary, MyMemoryTranslator({})]))
            result = translator.translate("会议将于\n明天开始。")
        self.assertEqual(requests[0]["q"], "会议将于明天开始。")
        self.assertEqual(result["original"], "会议将于\n明天开始。")
        self.assertEqual(translator.name(), "MyMemory 翻译")

    def test_two_paragraphs_rate_limited_and_preserved(self):
        delegate = BaiduTranslator(CFG)
        calls = []

        def post(url, data=None, **kwargs):
            calls.append(dict(data))
            return _FakeResponse(_ok_payload(["Translation " + str(len(calls))]))

        with mock.patch("translator.baidu.requests.post", side_effect=post), \
                mock.patch("translator.baidu.time.monotonic", return_value=100.0), \
                mock.patch("translator.baidu.time.sleep") as sleep:
            result = ParagraphTranslator(delegate).translate("第一\n段。\n\n第二\n段。")
        self.assertEqual([call["q"] for call in calls], ["第一段。", "第二段。"])
        self.assertEqual(result["translated"], "Translation 1\n\nTranslation 2")
        sleep.assert_called_once_with(1.0)

    def test_mymemory_explicit_target_not_ignored(self):
        with mock.patch("translator.mymemory.requests.get") as get:
            result = MyMemoryTranslator({}).translate("Python", "en")
        get.assert_not_called()
        self.assertEqual(result["translated"], "Python")
        self.assertEqual(result["target_lang"], "en")


if __name__ == "__main__":
    unittest.main()
