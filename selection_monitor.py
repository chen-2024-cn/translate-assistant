"""
文本选择检测模块 (纯 pywin32，零 ctypes)
QTimer 轮询左键 → 判断是否真的在"选字" → 按触发方式/前台程序过滤 → 模拟 Ctrl+C 取文本
"""
import math
import os
import time

import pyperclip
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

import config
import settings
import text_filter

import win32api
import win32con
import win32gui
import win32process

_DRAG_MIN_PIXELS = 6        # 按下→松开位移超过它才算拖选
_DOUBLE_CLICK_SECS = 0.4    # 双击选词的最大间隔
_DOUBLE_CLICK_PIXELS = 4    # 双击两次点击的最大位移


def _foreground_process_name() -> str:
    """前台窗口所属进程名(小写)，取不到返回空串"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return ""
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
            False, pid,
        )
        try:
            return os.path.basename(
                win32process.GetModuleFileNameEx(handle, 0)
            ).lower()
        finally:
            win32api.CloseHandle(handle)
    except Exception:
        return ""


_LOG_FILE = os.path.join(settings.APP_DIR, "debug.log")
_LOG_MAX_BYTES = 200 * 1024


def _log(msg: str):
    """诊断日志: 只记判断结果和进程名, 不记选中的文字"""
    if not config.DEBUG_LOG:
        return
    try:
        os.makedirs(settings.APP_DIR, exist_ok=True)
        if os.path.exists(_LOG_FILE) and os.path.getsize(_LOG_FILE) > _LOG_MAX_BYTES:
            os.remove(_LOG_FILE)
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + msg + "\n")
    except Exception:
        pass


def _is_own_window(hwnd=None) -> bool:
    try:
        hwnd = win32gui.GetForegroundWindow() if hwnd is None else hwnd
        return bool(hwnd) and win32process.GetWindowThreadProcessId(hwnd)[1] == os.getpid()
    except Exception:
        return False


def _ctrl_down() -> bool:
    try:
        return bool(win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000)
    except Exception:
        return False


class SelectionMonitor(QObject):
    """QTimer 轮询左键状态 → 模拟 Ctrl+C → 获取选中文本"""

    text_selected = pyqtSignal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)
        self._running = False
        self._was_pressed = False
        self._press_pos = (0, 0)
        self._ctrl_during_press = False
        self._last_release_time = 0.0
        self._last_release_pos = (0, 0)
        self._ignore_until = 0.0
        self._last_detect_time = 0.0
        self._busy = False
        self._pending_read = False
        self._old_clipboard = ""
        self._copy_via_insert = False
        self._clipboard_cleared = False
        self._source_hwnd = None

        saved = settings.load()
        self.enabled = saved["enabled"]
        self.trigger_mode = saved["trigger_mode"]

    # ── 公开接口 ───────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._timer.start(60)

    def stop(self):
        self._running = False
        self._timer.stop()

    def set_ignore_window(self, duration: float = 0.8):
        self._ignore_until = time.time() + duration

    def set_busy(self, busy: bool):
        self._busy = busy

    def set_enabled(self, enabled: bool):
        self.enabled = enabled
        self._save()

    def set_trigger_mode(self, mode: str):
        self.trigger_mode = mode
        self._save()

    def _save(self):
        settings.save({"enabled": self.enabled, "trigger_mode": self.trigger_mode})

    # ── 轮询 ───────────────────────────────────────────────────

    def _poll(self):
        if not self._running:
            return

        try:
            pressed = bool(win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000)
        except Exception:
            return

        if pressed and not self._was_pressed:
            self._press_pos = win32api.GetCursorPos()
            self._ctrl_during_press = False
        if pressed and _ctrl_down():
            self._ctrl_during_press = True

        if self._was_pressed and not pressed:
            self._on_left_up()
        self._was_pressed = pressed

    def _is_selection_gesture(self, release_pos, now) -> bool:
        """拖选 或 双击 才算选字，单击不触发"""
        dx = release_pos[0] - self._press_pos[0]
        dy = release_pos[1] - self._press_pos[1]
        if math.hypot(dx, dy) >= _DRAG_MIN_PIXELS:
            return True
        ddx = release_pos[0] - self._last_release_pos[0]
        ddy = release_pos[1] - self._last_release_pos[1]
        return (now - self._last_release_time <= _DOUBLE_CLICK_SECS
                and math.hypot(ddx, ddy) <= _DOUBLE_CLICK_PIXELS)

    def _on_left_up(self):
        now = time.time()
        release_pos = win32api.GetCursorPos()
        is_gesture = self._is_selection_gesture(release_pos, now)
        self._last_release_time = now
        self._last_release_pos = release_pos

        proc = _foreground_process_name()
        ctrl = self._ctrl_during_press or _ctrl_down()
        head = (f"松开左键 进程={proc or '?'} 模式={self.trigger_mode} "
                f"开关={'开' if self.enabled else '关'} Ctrl={'是' if ctrl else '否'} "
                f"拖选/双击={'是' if is_gesture else '否'}")

        if _is_own_window():
            return _log(head + " -> 忽略: 翻译助手自身窗口")
        if not self.enabled:
            return _log(head + " -> 忽略: 划词翻译已关闭")
        if now < self._ignore_until:
            return _log(head + " -> 忽略: 弹窗刚关闭的冷却期")
        if self._busy:
            return _log(head + " -> 忽略: 上一次翻译还没结束")
        if not is_gesture:
            return _log(head + " -> 忽略: 只是单击")
        if now - self._last_detect_time < 0.5:
            return _log(head + " -> 忽略: 距上次触发太近")
        is_terminal = proc in {p.lower() for p in config.TERMINAL_PROCESSES}
        if self.trigger_mode == settings.MODE_CTRL:
            if not ctrl:
                return _log(head + " -> 忽略: Ctrl 模式下没按 Ctrl")
        elif is_terminal:
            return _log(head + " -> 忽略: 终端程序 (选中即译模式不处理终端)")
        elif proc in {p.lower() for p in config.IGNORE_PROCESSES}:
            return _log(head + " -> 忽略: 编辑器/IDE")

        self._copy_via_insert = is_terminal
        _log(head + (" -> 开始取词 (终端: 用 Ctrl+Insert)" if is_terminal else " -> 开始取词"))
        self._last_detect_time = now
        source_hwnd = win32gui.GetForegroundWindow()
        QTimer.singleShot(int(config.SELECTION_DELAY * 1000),
                          lambda: self._begin_detect(source_hwnd))

    # ── 文本提取 ───────────────────────────────────────────────

    def _begin_detect(self, source_hwnd=None):
        if (self._pending_read or not self._running or not self.enabled or self._busy
                or time.time() < self._ignore_until or _is_own_window()):
            return
        current_hwnd = win32gui.GetForegroundWindow()
        if source_hwnd is not None and current_hwnd != source_hwnd:
            return _log("  取词取消: 前台窗口已改变")
        self._source_hwnd = current_hwnd
        self._pending_read = True
        self._clipboard_cleared = False

        try:
            self._old_clipboard = pyperclip.paste()
        except Exception:
            self._pending_read = False
            return _log("  取词取消: 无法备份剪贴板")

        # 先清空剪贴板再发 Ctrl+C (哨兵法):
        # 旧逻辑靠"Ctrl+C 前后剪贴板是否变化"判断取词, 但重复选中与当前剪贴板
        # 相同的文字时剪贴板不会变 → 被误判为"没选中", 第二次翻译静默失败。
        # 清空后: Ctrl+C 之后仍为空 = 没取到词; 有内容 = 成功(即使与原剪贴板相同)。
        try:
            pyperclip.copy("")
            self._clipboard_cleared = True
        except Exception:
            pass

        try:
            self._send_ctrl_c()
        except Exception:
            self._pending_read = False
            if self._clipboard_cleared:
                self._restore_clipboard(self._old_clipboard)
            return _log("  取词失败: 无法发送复制按键")
        QTimer.singleShot(120, self._finish_detect)

    def _finish_detect(self):
        self._pending_read = False

        old = self._old_clipboard
        try:
            new = pyperclip.paste()
        except Exception:
            if self._clipboard_cleared:
                self._restore_clipboard(old)
            return

        # 预清空成功后,即使复制的单词与原剪贴板相同也属于有效取词。
        copied = bool(new) and (self._clipboard_cleared or new != old)
        if self._clipboard_cleared or new != old:
            self._restore_clipboard(old)
        if not copied:
            return _log("  取词失败: 没有新的复制结果或剪贴板被占用")
        if (not self._running or not self.enabled or self._busy or _is_own_window()
                or win32gui.GetForegroundWindow() != self._source_hwnd):
            return _log("  取词取消: 当前窗口或监听状态已改变")

        selected = new.strip()
        if len(selected) < config.MIN_TEXT_LENGTH:
            return _log("  忽略: 选中内容为空白")
        if len(selected) > config.MAX_TEXT_LENGTH:
            selected = selected[: config.MAX_TEXT_LENGTH]

        if self.trigger_mode == settings.MODE_AUTO:
            if not text_filter.has_translatable_text(selected):
                return _log("  忽略: 没有字母或汉字")
            if config.SKIP_CODE_LIKE and text_filter.looks_like_code(selected):
                return _log("  忽略: 像代码/路径")

        _log(f"  取词成功 {len(selected)} 个字符, 开始翻译")
        x, y = win32api.GetCursorPos()
        self.text_selected.emit(selected, x, y)

    @staticmethod
    def _restore_clipboard(text):
        try:
            pyperclip.copy(text)
        except Exception:
            _log("  剪贴板恢复失败: 被其他程序占用")

    # ── 模拟按键 ──────────────────────────────────────────────

    def _send_ctrl_c(self):
        """普通程序发 Ctrl+C; 终端里发 Ctrl+Insert (同样是复制, 但不会变成中断信号)"""
        if self._copy_via_insert:
            key, flags = win32con.VK_INSERT, win32con.KEYEVENTF_EXTENDEDKEY
        else:
            key, flags = 0x43, 0
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(key, 0, flags, 0)
        win32api.keybd_event(key, 0, flags | win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
