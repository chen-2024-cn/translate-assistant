"""快捷键注册生命周期与消息过滤回归,注册调用使用 mock。"""
from ctypes import addressof, wintypes
import unittest
from unittest import mock

import win32con
import win32gui
from PyQt5.QtWidgets import QApplication
from global_hotkey import GlobalHotkey, _HOTKEY_ID

_APP = QApplication.instance() or QApplication([])


class TestGlobalHotkey(unittest.TestCase):
    def test_start_stop_idempotent(self):
        app = mock.Mock()
        # QObject parent需要真实Qt对象,随后用 mock 观察过滤器安装。
        hotkey = GlobalHotkey(_APP)
        hotkey._app = app
        with mock.patch("global_hotkey.win32gui.RegisterHotKey") as register, \
                mock.patch("global_hotkey.win32gui.UnregisterHotKey") as unregister:
            self.assertTrue(hotkey.start())
            self.assertTrue(hotkey.start())
            register.assert_called_once()
            self.assertEqual(register.call_args.args[2], win32con.MOD_ALT | 0x4000)
            hotkey.stop()
            hotkey.stop()
            unregister.assert_called_once()
        self.assertFalse(hotkey.registered)
        app.installNativeEventFilter.assert_called_once()
        app.removeNativeEventFilter.assert_called_once()

    def test_conflict_reported(self):
        hotkey = GlobalHotkey(_APP)
        hotkey._app = mock.Mock()
        with mock.patch("global_hotkey.win32gui.RegisterHotKey", side_effect=win32gui.error(1409, "RegisterHotKey", "already registered")):
            self.assertFalse(hotkey.start())
        self.assertFalse(hotkey.registered)
        self.assertIn("1409", hotkey.error)
        hotkey._app.installNativeEventFilter.assert_not_called()

    def test_only_matching_native_hotkey_activates(self):
        hotkey = GlobalHotkey(_APP)
        hotkey.registered = True
        events = []
        hotkey.activated.connect(lambda: events.append(True))
        message = wintypes.MSG()
        message.message = win32con.WM_HOTKEY
        message.wParam = _HOTKEY_ID
        self.assertEqual(hotkey._filter.nativeEventFilter(b"windows_dispatcher_MSG", addressof(message)), (True, 0))
        self.assertEqual(len(events), 1)
        message.wParam += 1
        self.assertEqual(hotkey._filter.nativeEventFilter(b"windows_dispatcher_MSG", addressof(message)), (False, 0))
        hotkey.registered = False
        self.assertEqual(len(events), 1)


if __name__ == "__main__":
    unittest.main()
