"""回归测试: .env 加载与日志基础设施。

覆盖用户实际踩到的两个坑:
1. 项目不会自动加载 .env, 导致"我把 appid/secret 填进 .env 了却还是用不上"
2. 双击启动没有控制台, 出错后没有任何可查的日志
"""
import logging
import os
import sys
import tempfile
import unittest
from pathlib import Path

import config
import logging_setup


class DotenvTests(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in ("TA_DOTENV_A", "TA_DOTENV_B", "TA_DOTENV_C")}
        for key in self._saved:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _write(self, text: str) -> Path:
        handle = tempfile.NamedTemporaryFile("w", suffix=".env", delete=False, encoding="utf-8")
        handle.write(text)
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return Path(handle.name)

    def test_parses_plain_quoted_and_export_forms(self):
        path = self._write(
            "# comment line\n"
            "\n"
            "TA_DOTENV_A=plain\n"
            'TA_DOTENV_B="quoted value"\n'
            "export TA_DOTENV_C='single'\n"
            "MALFORMED_LINE_WITHOUT_EQUALS\n"
        )
        loaded = config.load_dotenv(path)
        self.assertEqual(sorted(loaded), ["TA_DOTENV_A", "TA_DOTENV_B", "TA_DOTENV_C"])
        self.assertEqual(os.environ["TA_DOTENV_A"], "plain")
        self.assertEqual(os.environ["TA_DOTENV_B"], "quoted value")
        self.assertEqual(os.environ["TA_DOTENV_C"], "single")

    def test_existing_environment_wins(self):
        os.environ["TA_DOTENV_A"] = "from-env"
        path = self._write("TA_DOTENV_A=from-file\n")
        self.assertEqual(config.load_dotenv(path), [])
        self.assertEqual(os.environ["TA_DOTENV_A"], "from-env")

    def test_missing_file_is_not_an_error(self):
        self.assertEqual(config.load_dotenv(Path(tempfile.gettempdir()) / "no-such-file.env"), [])

    def test_bom_and_crlf_are_tolerated(self):
        path = self._write("\ufeffTA_DOTENV_A=windows\r\nTA_DOTENV_B=crlf\r\n")
        config.load_dotenv(path)
        self.assertEqual(os.environ["TA_DOTENV_A"], "windows")
        self.assertEqual(os.environ["TA_DOTENV_B"], "crlf")


class LoggingTests(unittest.TestCase):
    def test_log_file_is_created_and_written(self):
        path = logging_setup.setup_logging()
        logging.getLogger("test").info("写入测试")
        for handler in logging.getLogger().handlers:
            handler.flush()
        self.assertTrue(path.is_file(), f"日志文件未创建: {path}")
        self.assertIn("写入测试", path.read_text(encoding="utf-8"))

    def test_exception_hooks_do_not_raise(self):
        logging_setup.install_exception_hooks()
        self.assertIsNotNone(os.sys.excepthook)


if __name__ == "__main__":
    unittest.main()
