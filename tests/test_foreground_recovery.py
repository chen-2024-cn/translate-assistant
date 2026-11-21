"""回归测试: 召回面板时必须真正拿到前台, 且失败要留痕。

用户实测症状: 缩小 → 勾选置顶 → 点 X 收进托盘 → Alt+1 召回 → 打不了字。
根因(本机实测): Windows 的前台锁会静默拒绝后台进程的 SetForegroundWindow,
面板置顶可见但键盘输入仍留在别的程序; 旧代码用 Qt 的 isActiveWindow() 判断,
它在这种情况下仍返回 True, 于是既不重试也不记日志 —— 假成功。
"""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


class ForegroundRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PyQt5.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def _panel(self):
        from panel_ui import TranslatePanel

        return TranslatePanel()

    def test_present_forces_foreground_when_os_says_another_window_has_it(self):
        """前台是别的窗口时必须走抢前台, 不能信 Qt 的 isActiveWindow()。"""
        panel = self._panel()
        calls = []
        with patch("panel_ui.win32gui.GetForegroundWindow", return_value=0xDEAD), \
                patch.object(panel, "_native_is_foreground", return_value=False), \
                patch.object(panel, "_force_foreground", side_effect=lambda: calls.append(1)), \
                patch.object(panel, "_request_input_focus"):
            panel.present()
        self.assertEqual(calls, [1], "前台不属于本窗口时必须调用 _force_foreground()")

    def test_present_skips_forcing_when_already_foreground(self):
        panel = self._panel()
        calls = []
        with patch.object(panel, "_native_is_foreground", return_value=True), \
                patch.object(panel, "_force_foreground", side_effect=lambda: calls.append(1)), \
                patch.object(panel, "_request_input_focus"):
            panel.present()
        self.assertEqual(calls, [], "已经在前台时不应反复抢焦点")

    def test_focus_retry_does_not_abandon_after_180ms(self):
        """旧代码重试 12 次 × 15ms 就放弃(实际窗口激活常更慢), 现在按 1.5s 截止时间兜底。"""
        panel = self._panel()
        panel.show()
        tries = []
        with patch.object(panel, "_native_is_foreground", return_value=False), \
                patch.object(panel, "_force_foreground", side_effect=lambda: tries.append(1)):
            panel._request_input_focus()
            for _ in range(20):  # 20 次 × 60ms = 1.2s, 仍未拿到前台
                panel._complete_input_focus()
        self.assertTrue(panel._focus_requested, "1.5s 内不应提前放弃聚焦请求")
        self.assertTrue(tries, "抢前台失败后应在重试里继续尝试")

    def test_native_focus_check_uses_getforegroundwindow_not_qt(self):
        """Qt 的 isActiveWindow() 会在抢前台失败时返回 True, 不能作为判断依据。"""
        panel = self._panel()
        with patch("panel_ui._real_window_backend", return_value=True), \
                patch("panel_ui.win32gui.GetForegroundWindow", return_value=0x1234), \
                patch.object(panel, "winId", return_value=0x1234):
            self.assertTrue(panel._native_is_foreground())
        with patch("panel_ui._real_window_backend", return_value=True), \
                patch("panel_ui.win32gui.GetForegroundWindow", return_value=0x9999), \
                patch.object(panel, "winId", return_value=0x1234):
            self.assertFalse(panel._native_is_foreground())

    def test_activation_returns_focus_from_pin_checkbox_to_input(self):
        """点过置顶复选框后重开面板, 焦点要回到原文输入框, 否则按键被复选框吃掉。"""
        panel = self._panel()
        calls = []
        original = panel.input_edit.setFocus
        panel.input_edit.setFocus = lambda *a, **k: calls.append(a)
        try:
            with patch("panel_ui.QApplication.focusWidget", return_value=panel.pin_box):
                panel._restore_input_focus_on_activate()
        finally:
            panel.input_edit.setFocus = original
        self.assertEqual(len(calls), 1, "焦点停在置顶复选框上时必须交还给输入框")

    def test_activation_returns_focus_when_nothing_has_it(self):
        panel = self._panel()
        calls = []
        original = panel.input_edit.setFocus
        panel.input_edit.setFocus = lambda *a, **k: calls.append(a)
        try:
            with patch("panel_ui.QApplication.focusWidget", return_value=None):
                panel._restore_input_focus_on_activate()
        finally:
            panel.input_edit.setFocus = original
        self.assertEqual(len(calls), 1, "焦点落空时必须交还给输入框")

    def test_activation_does_not_steal_focus_from_other_widgets(self):
        panel = self._panel()
        calls = []
        original = panel.input_edit.setFocus
        panel.input_edit.setFocus = lambda *a, **k: calls.append(a)
        try:
            with patch("panel_ui.QApplication.focusWidget", return_value=panel.vocabulary_btn):
                panel._restore_input_focus_on_activate()
        finally:
            panel.input_edit.setFocus = original
        self.assertEqual(calls, [], "用户主动点的其他控件不应被抢走焦点")

    def test_pin_checkbox_never_takes_keyboard_focus(self):
        """置顶复选框不抢焦点, 从源头避免"点过它就打不了字"。"""
        from PyQt5.QtCore import Qt

        panel = self._panel()
        self.assertEqual(panel.pin_box.focusPolicy(), Qt.NoFocus)

    def test_input_focus_no_longer_forces_native_child_window(self):
        """SetFocus(input_edit.winId()) 会凭空造出一个原生子窗口, 实测也拿不到原生焦点。"""
        import inspect

        import panel_ui

        source = inspect.getsource(panel_ui.TranslatePanel._complete_input_focus)
        self.assertNotIn("win32gui.SetFocus", source)
        self.assertNotIn("input_edit.winId", source)


if __name__ == "__main__":
    unittest.main()
