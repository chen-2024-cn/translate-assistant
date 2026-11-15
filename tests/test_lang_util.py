"""lang_util 回归测试
必须永远覆盖线上事故用例: "明天预期什么时候" 被 langdetect 误判为韩语,
导致 MyMemory 以 ko|zh-CN 语言对返回垃圾译文 "时间段为"
"""
import unittest

from translator.lang_util import (
    detect_script, lang_pair, result_matches_target, is_noop_translation
)


class TestDetectScript(unittest.TestCase):
    def test_incident_text_is_chinese(self):
        # 事故回归: langdetect 对此句判 ko(置信度0.9999), 脚本检测必须判 zh
        self.assertEqual(detect_script("明天预期什么时候"), "zh")

    def test_short_chinese(self):
        for t in ("你好", "什么时候", "翻译", "预期", "。"):
            if t == "。":
                continue  # 纯标点无脚本
            self.assertEqual(detect_script(t), "zh", t)

    def test_english(self):
        self.assertEqual(detect_script("hello world"), "en")

    def test_korean(self):
        self.assertEqual(detect_script("안녕하세요"), "ko")

    def test_japanese(self):
        self.assertEqual(detect_script("こんにちは"), "ja")

    def test_digits_symbols_unknown(self):
        self.assertEqual(detect_script("12345 !!"), "unknown")


class TestLangPair(unittest.TestCase):
    def test_chinese_to_english(self):
        # 事故回归: 必须走 zh-CN|en, 绝不允许 ko|zh-CN
        self.assertEqual(lang_pair("明天预期什么时候"), ("zh-CN", "en"))

    def test_english_to_chinese(self):
        self.assertEqual(lang_pair("hello world"), ("en", "zh-CN"))

    def test_korean_to_chinese(self):
        self.assertEqual(lang_pair("안녕하세요"), ("ko", "zh-CN"))

    def test_unknown_defaults_to_english_source(self):
        self.assertEqual(lang_pair("12345"), ("en", "zh-CN"))


class TestResultGate(unittest.TestCase):
    def test_garbage_chinese_for_english_target_rejected(self):
        # 事故回归: 目标英文却返回汉字垃圾 "时间段为" → 必须拒绝
        self.assertFalse(result_matches_target("时间段为", "en"))

    def test_english_result_for_english_target_ok(self):
        self.assertTrue(result_matches_target("What time do you expect tomorrow?", "en"))

    def test_chinese_result_for_chinese_target_ok(self):
        self.assertTrue(result_matches_target("你好世界", "zh-CN"))

    def test_empty_rejected(self):
        self.assertFalse(result_matches_target("", "en"))
        self.assertFalse(result_matches_target("   ", "en"))


class TestMixedScriptRegression(unittest.TestCase):
    """事故回归: 中英混排句 '配好后，PyCharm 的 Terminal...' 汉字18个 < 拉丁字母25个,
    旧'数量最多'逻辑误判为 en → 走'译成中文'方向 → 百度中→中原样返回, 用户看到的还是原文"""

    INCIDENT = "配好后，PyCharm 的 Terminal 会自动帮你激活，右下角也会显示 Python 3.14 (.venv)。"

    def test_incident_sentence_is_chinese(self):
        self.assertEqual(detect_script(self.INCIDENT), "zh")

    def test_incident_sentence_direction(self):
        self.assertEqual(lang_pair(self.INCIDENT), ("zh-CN", "en"))

    def test_embedded_terms_do_not_flip_direction(self):
        for s in ("请使用 Python 编写一个 hello world 程序",
                  "在 PyCharm 中打开 Terminal 面板",
                  "这个 API 返回 JSON 格式的数据"):
            self.assertEqual(detect_script(s), "zh", s)

    def test_pure_english_still_en(self):
        self.assertEqual(detect_script("Please install the package first"), "en")


class TestNoopDetection(unittest.TestCase):
    def test_chinese_identical_result_is_noop(self):
        s = "配好后，PyCharm 会自动激活。"
        self.assertTrue(is_noop_translation(s, s, "zh"))
        self.assertTrue(is_noop_translation(s, s, "zh-CN"))

    def test_proper_noun_identical_is_ok(self):
        # "Python"→"Python" 专有名词原样输出是合法结果 (不含汉字, 不判空翻译)
        self.assertFalse(is_noop_translation("Python", "Python", "zh-CN"))

    def test_target_english_not_checked(self):
        # 目标为英文时不做该项检查 (由 result_matches_target 质量门负责)
        self.assertFalse(is_noop_translation("你好世界", "你好世界", "en"))

    def test_different_result_not_noop(self):
        self.assertFalse(is_noop_translation("你好世界", "Hello world", "zh-CN"))


if __name__ == "__main__":
    unittest.main()
