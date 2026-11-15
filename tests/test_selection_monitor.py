"""取词回归,所有剪贴板与系统复制调用mock,不触及用户剪贴板。"""
import time
import unittest
from unittest import mock
from PyQt5.QtWidgets import QApplication
from selection_monitor import SelectionMonitor

_APP = QApplication.instance() or QApplication([])


class TestSelectionMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = SelectionMonitor()
        self.monitor._running = True
        self.monitor.enabled = True
        self.monitor._source_hwnd = 100
        self.monitor._old_clipboard = "expect"
        self.monitor._clipboard_cleared = True
        self.events = []
        self.monitor.text_selected.connect(lambda *args: self.events.append(args))
        self.patches = [
            mock.patch("selection_monitor._is_own_window", return_value=False),
            mock.patch("selection_monitor.win32gui.GetForegroundWindow", return_value=100),
            mock.patch("selection_monitor.win32api.GetCursorPos", return_value=(30, 40)),
            mock.patch("selection_monitor._log"),
        ]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_same_word_as_original_clipboard_is_valid(self):
        with mock.patch("selection_monitor.pyperclip.paste", return_value="expect"), \
                mock.patch("selection_monitor.pyperclip.copy") as copy:
            self.monitor._finish_detect()
        self.assertEqual(self.events[0][0], "expect")
        copy.assert_called_once_with("expect")

    def test_failed_preclear_and_unchanged_text_not_translation(self):
        self.monitor._clipboard_cleared = False
        with mock.patch("selection_monitor.pyperclip.paste", return_value="expect"), \
                mock.patch("selection_monitor.pyperclip.copy") as copy:
            self.monitor._finish_detect()
        self.assertFalse(self.events)
        copy.assert_not_called()

    def test_empty_response_restores_original(self):
        with mock.patch("selection_monitor.pyperclip.paste", return_value=""), \
                mock.patch("selection_monitor.pyperclip.copy") as copy:
            self.monitor._finish_detect()
        self.assertFalse(self.events)
        copy.assert_called_once_with("expect")

    def test_clipboard_read_failure_restores_original(self):
        with mock.patch("selection_monitor.pyperclip.paste", side_effect=RuntimeError()), \
                mock.patch("selection_monitor.pyperclip.copy") as copy:
            self.monitor._finish_detect()
        copy.assert_called_once_with("expect")
        self.assertFalse(self.events)

    def test_own_window_skips_begin_without_clipboard_access(self):
        with mock.patch("selection_monitor._is_own_window", return_value=True), \
                mock.patch("selection_monitor.pyperclip.paste") as paste:
            self.monitor._begin_detect(100)
        paste.assert_not_called()

    def test_changed_window_cancels_begin(self):
        with mock.patch("selection_monitor.pyperclip.paste") as paste:
            self.monitor._begin_detect(200)
        paste.assert_not_called()

    def test_own_window_cancels_pending_copy_after_restore(self):
        with mock.patch("selection_monitor._is_own_window", return_value=True), \
                mock.patch("selection_monitor.pyperclip.paste", return_value="time"), \
                mock.patch("selection_monitor.pyperclip.copy") as copy:
            self.monitor._finish_detect()
        self.assertFalse(self.events)
        copy.assert_called_once_with("expect")

    def test_stopped_monitor_does_not_copy(self):
        self.monitor._running = False
        with mock.patch("selection_monitor.pyperclip.paste") as paste:
            self.monitor._begin_detect(100)
        paste.assert_not_called()
