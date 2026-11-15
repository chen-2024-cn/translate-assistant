"""窗口切换/快捷键独立注册,不操作用户数据或真实热键。"""
from ctypes import addressof, wintypes
from unittest import mock
import win32con
import win32gui
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from tests.test_vocabulary import StoreCase, _APP
from global_hotkey import GlobalHotkey, _VOCABULARY_HOTKEY_ID
from tray_manager import TrayManager
from popup_ui import TranslatePopup


class TestWindowToggles(StoreCase):
    def setUp(self):
        super().setUp()
        self.monitor = mock.Mock(enabled=True, trigger_mode="ctrl")
        self.tray = TrayManager(_APP, self.monitor, vocabulary=self.store)

    def tearDown(self):
        for window in (self.tray._panel, self.tray._vocabulary_window):
            if window is not None:
                window.close()
        self.tray.hide()
        super().tearDown()

    def test_panel_open_hide_reopen_same_instance_and_content(self):
        self.tray.toggle_panel()
        panel = self.tray._panel
        panel.input_edit.setPlainText("keep input")
        self.assertTrue(panel.isVisible())
        self.tray.toggle_panel()
        self.assertFalse(panel.isVisible())
        self.assertFalse(panel._focus_timer.isActive())
        self.tray.toggle_panel()
        self.assertIs(self.tray._panel, panel)
        self.assertTrue(panel.isVisible())
        self.assertEqual(panel.input_edit.toPlainText(), "keep input")

    def test_minimized_panel_restored_not_hidden(self):
        self.tray.toggle_panel()
        panel = self.tray._panel
        panel.showMinimized()
        self.tray.toggle_panel()
        self.assertFalse(panel.isMinimized())
        self.assertTrue(panel.isVisible())

    def test_book_toggle_preserves_search_and_database(self):
        self.store.add("time", "n. 时间")
        self.tray.toggle_vocabulary()
        book = self.tray._vocabulary_window
        book.search_edit.setText("time")
        self.tray.toggle_vocabulary()
        self.assertFalse(book.isVisible())
        self.tray.toggle_vocabulary()
        self.assertIs(self.tray._vocabulary_window, book)
        self.assertEqual(book.search_edit.text(), "time")
        self.assertEqual(book.word_list.count(), 1)
        self.assertEqual(len(self.store.search()), 1)

    def test_minimized_book_restored(self):
        self.tray.toggle_vocabulary()
        book = self.tray._vocabulary_window
        book.showMinimized()
        self.tray.toggle_vocabulary()
        self.assertTrue(book.isVisible())
        self.assertFalse(book.isMinimized())

    def test_popup_opens_shared_book_toggle_can_hide(self):
        popup = TranslatePopup(vocabulary=self.store, on_open_vocabulary=self.tray._on_show_vocabulary)
        popup.open_vocabulary_btn.click()
        book = self.tray._vocabulary_window
        self.assertTrue(book.isVisible())
        self.assertIsNone(popup._vocabulary_window)
        self.tray.toggle_vocabulary()
        self.assertFalse(book.isVisible())
        popup.close()

    def test_one_hotkey_conflict_does_not_block_other(self):
        panel_key = GlobalHotkey(_APP)
        book_key = GlobalHotkey(_APP, ord("2"), _VOCABULARY_HOTKEY_ID)
        with mock.patch("global_hotkey.win32gui.RegisterHotKey", side_effect=[
            win32gui.error(1409, "RegisterHotKey", "already registered"), None]), \
                mock.patch("global_hotkey.win32gui.UnregisterHotKey") as unregister:
            self.assertFalse(panel_key.start())
            self.assertTrue(book_key.start())
            self.assertFalse(panel_key.registered)
            self.assertTrue(book_key.registered)
            book_key.stop()
            unregister.assert_called_once_with(None, _VOCABULARY_HOTKEY_ID)

    def test_alt_two_native_signal_is_separate(self):
        panel_key = GlobalHotkey(_APP)
        book_key = GlobalHotkey(_APP, ord("2"), _VOCABULARY_HOTKEY_ID)
        panel_key.registered = book_key.registered = True
        panel_events, book_events = [], []
        panel_key.activated.connect(lambda: panel_events.append(1))
        book_key.activated.connect(lambda: book_events.append(1))
        message = wintypes.MSG()
        message.message = win32con.WM_HOTKEY
        message.wParam = _VOCABULARY_HOTKEY_ID
        self.assertEqual(panel_key._filter.nativeEventFilter(b"windows_dispatcher_MSG", addressof(message)), (False, 0))
        self.assertEqual(book_key._filter.nativeEventFilter(b"windows_dispatcher_MSG", addressof(message)), (True, 0))
        self.assertFalse(panel_events)
        self.assertEqual(book_events, [1])
        panel_key.registered = book_key.registered = False
