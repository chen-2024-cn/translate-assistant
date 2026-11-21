"""回归测试: 置顶开关不能重建原生窗口。

用户实测症状: 面板缩到最小 → 勾选"置顶" → 点右上角 X → 重新打开 → 输入框打不进字。
根因是 setWindowFlag() 对已显示窗口会销毁并重建原生窗口(HWND), 焦点/输入法上下文
随之丢失。修复方式是用 Win32 SetWindowPos 只改 Z 序。以下测试锁死这个行为。
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class PinToggleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt5.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def _panel(self):
        from panel_ui import TranslatePanel

        return TranslatePanel()

    def test_pin_uses_setwindowpos_and_never_touches_window_flags(self):
        panel = self._panel()
        flag_calls = []
        panel.setWindowFlag = lambda *args, **kwargs: flag_calls.append(args)
        panel._apply_topmost = lambda on: True

        panel._on_pin(True)
        panel._on_pin(False)

        self.assertEqual(flag_calls, [], "置顶不应调用 setWindowFlag(会重建原生窗口)")
        self.assertFalse(panel.pin_box.isChecked())

    def test_fallback_path_keeps_checkbox_in_sync(self):
        panel = self._panel()
        panel._apply_topmost = lambda on: False  # 模拟非 Windows / 调用失败

        panel._on_pin(True)

        self.assertTrue(panel.pin_box.isChecked(), "兜底路径后勾选状态必须与真实状态一致")

    def test_focus_helper_records_deadline(self):
        panel = self._panel()
        panel._request_input_focus(select_all=True)
        self.assertGreater(panel._focus_deadline, 0)
        self.assertTrue(panel._focus_select_all or not panel._focus_requested)


if __name__ == "__main__":
    unittest.main()
