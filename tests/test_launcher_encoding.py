"""回归测试: run_silent.vbs 必须是纯 ASCII。

用户实测症状: 双击 run.bat → 弹出 Windows Script Host 错误
"run_silent.vbs 行 17 字符 44 无效字符 800A0408"。
根因: WSH 按系统 ANSI 代码页(中文系统为 GBK)读取 .vbs, 而文件是无 BOM 的 UTF-8,
中文字节被错误解码成非法字符, 编译阶段即失败。修复方式是脚本只保留 ASCII。
"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class LauncherEncodingTests(unittest.TestCase):
    def test_vbs_launchers_are_ascii_only(self):
        scripts = sorted(ROOT.glob("*.vbs"))
        self.assertTrue(scripts, "expected at least run_silent.vbs in project root")
        for path in scripts:
            data = path.read_bytes()
            bad = [i for i, b in enumerate(data) if b > 0x7F]
            with self.subTest(script=path.name):
                self.assertEqual(
                    bad, [],
                    f"{path.name} has non-ASCII bytes at offsets {bad[:5]}; "
                    "WSH reads .vbs in the ANSI codepage, keep it ASCII-only",
                )


if __name__ == "__main__":
    unittest.main()
