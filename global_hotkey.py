"""Windows Alt+数字全局快捷键: 独立注册,通过Qt主线程接收消息。"""
from ctypes import wintypes

from PyQt5.QtCore import QAbstractNativeEventFilter, QObject, pyqtSignal
import win32con
import win32gui

_HOTKEY_ID = 0x5411
_VOCABULARY_HOTKEY_ID = 0x5412
_MODIFIERS = win32con.MOD_ALT | 0x4000  # MOD_NOREPEAT
_VIRTUAL_KEY = ord("1")


class _HotkeyEventFilter(QAbstractNativeEventFilter):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def nativeEventFilter(self, event_type, message):
        if bytes(event_type) in (b"windows_generic_MSG", b"windows_dispatcher_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if self.owner.registered and msg.message == win32con.WM_HOTKEY and msg.wParam == self.owner.hotkey_id:
                self.owner.activated.emit()
                return True, 0
        return False, 0


class GlobalHotkey(QObject):
    activated = pyqtSignal()

    def __init__(self, app, virtual_key=_VIRTUAL_KEY, hotkey_id=_HOTKEY_ID):
        super().__init__(app)
        self._app = app
        self.virtual_key = virtual_key
        self.hotkey_id = hotkey_id
        self.label = f"Alt+{chr(virtual_key)}"
        self._filter = _HotkeyEventFilter(self)
        self.registered = False
        self.error = ""

    def start(self) -> bool:
        if self.registered:
            return True
        try:
            win32gui.RegisterHotKey(None, self.hotkey_id, _MODIFIERS, self.virtual_key)
        except win32gui.error as e:
            self.error = f"{self.label} 注册失败,可能已被其他程序占用 (错误码 {e.winerror})"
            return False
        self.registered = True
        self._app.installNativeEventFilter(self._filter)
        self._app.aboutToQuit.connect(self.stop)
        self.error = ""
        return True

    def stop(self):
        if not self.registered:
            return
        try:
            win32gui.UnregisterHotKey(None, self.hotkey_id)
        except win32gui.error:
            pass
        finally:
            self.registered = False
            self._app.removeNativeEventFilter(self._filter)
