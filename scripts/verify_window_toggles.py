"""真实Alt+1/Alt+2窗口开关验收: 隔离词库,不网络翻译或操作剪贴板。
旧实例占用某组键时跳过该组并报告BLOCKED,只关闭自己创建的辅助进程。
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
import win32api
import win32con
import win32gui
import win32process

OUTPUT = ROOT / "artifacts" / "verification" / "window-toggles"
OUTPUT.mkdir(parents=True, exist_ok=True)

if "--helper" in sys.argv:
    qapp = QApplication([])
    window = QWidget()
    window.setWindowTitle("Translation Toggle Verification External Window")
    window.resize(500, 260)
    layout = QVBoxLayout(window)
    layout.addWidget(QLabel("独立前台窗口: 验证Alt+1/Alt+2开关"))
    window.show()
    sys.exit(qapp.exec_())

from main import TranslateApp
from vocabulary_store import VocabularyStore

TEMP = ROOT / "artifacts" / "test-temp"
TEMP.mkdir(parents=True, exist_ok=True)


def wait_for(predicate, seconds=8):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        QTest.qWait(30)
        if predicate():
            QTest.qWait(80)
            return
    raise RuntimeError("实际窗口状态未符合预期")


def helper_window(pid):
    found = []
    def visit(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32process.GetWindowThreadProcessId(hwnd)[1] == pid:
            found.append(hwnd)
    win32gui.EnumWindows(visit, None)
    return found[0] if found else None


def external_focus(hwnd):
    # 仅验证辅助进程前台切换;产品不模拟这些键。
    win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
    win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except win32gui.error:
        pass
    QTest.qWait(150)
    if win32gui.GetForegroundWindow() != hwnd:
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 50, 50, 0, 0,
                             win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
        win32api.SetCursorPos((100, 100))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
        QTest.qWait(90)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
        QTest.qWait(150)
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                             win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    assert win32gui.GetForegroundWindow() == hwnd, (hwnd, win32gui.GetForegroundWindow())


def alt_digit(digit, repeat=False):
    try:
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        win32api.keybd_event(ord(digit), 0, 0, 0)
        QTest.qWait(70)
        if repeat:
            for _ in range(4):
                win32api.keybd_event(ord(digit), 0, 0, 0)
                QTest.qWait(70)
    finally:
        win32api.keybd_event(ord(digit), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
    QTest.qWait(100)


def click(widget):
    QTest.qWait(150)
    point = widget.mapToGlobal(widget.rect().center())
    win32api.SetCursorPos((point.x(), point.y()))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
    QTest.qWait(90)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
    QTest.qWait(150)


with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
    store = VocabularyStore(Path(tmp) / "words.db")
    store.add("time", "n. 时间; 时刻", "验收示例")
    app = TranslateApp(vocabulary=store)
    helper = None
    blocked = []
    try:
        helper = subprocess.Popen([sys.executable, __file__, "--helper"])
        wait_for(lambda: helper_window(helper.pid) is not None)
        hwnd = helper_window(helper.pid)
        for digit, hotkey in (("1", app.hotkey), ("2", app.vocabulary_hotkey)):
            print(f"Alt+{digit} registered={hotkey.registered} {hotkey.error}")
            if not hotkey.registered:
                blocked.append(f"Alt+{digit}")
                continue
            external_focus(hwnd)
            alt_digit(digit)
            window = app.tray._panel if digit == "1" else app.tray._vocabulary_window
            assert window is not None
            wait_for(lambda: window.isVisible() and not window.isMinimized())
            assert win32gui.GetForegroundWindow() == int(window.winId())
            print(f"PASS Alt+{digit}: 外部进程前台按键打开目标窗口")
            if digit == "1":
                window.input_edit.setPlainText("keep input")
            else:
                window.search_edit.setText("time")
            window.grab().save(str(OUTPUT / f"alt{digit}_opened.png"))
            alt_digit(digit)
            wait_for(lambda: not window.isVisible())
            QTest.qWait(900)
            assert not window.isVisible()
            if digit == "1":
                assert not window._focus_timer.isActive()
            print(f"PASS Alt+{digit}: 第二次按键隐藏,没有迟到焦点重新显示窗口")
            external_focus(hwnd)
            alt_digit(digit, repeat=True)
            wait_for(lambda: window.isVisible())
            assert (app.tray._panel if digit == "1" else app.tray._vocabulary_window) is window
            if digit == "1":
                assert window.input_edit.toPlainText() == "keep input"
            else:
                assert window.search_edit.text() == "time" and window.word_list.count() == 1
            print(f"PASS probe Alt+{digit}: 再次打开同一窗口保留内容,按住连发只触发一次")
            window.showMinimized()
            external_focus(hwnd)
            alt_digit(digit)
            wait_for(lambda: window.isVisible() and not window.isMinimized())
            print(f"PASS probe Alt+{digit}: 最小化时按键恢复,不是隐藏")
            alt_digit(digit)
            wait_for(lambda: not window.isVisible())
        # 无论Alt+1是否占用,都验证面板按钮与弹框入口共享词库。
        app.tray._on_show_panel()
        panel = app.tray._panel
        QTest.qWait(350)
        click(panel.vocabulary_btn)
        book = app.tray._vocabulary_window
        assert book is not None and book.isVisible()
        if app.vocabulary_hotkey.registered:
            alt_digit("2")
            wait_for(lambda: not book.isVisible())
        else:
            book.hide()
        panel.hide()
        app.popup.show_result("time", "n. 时间", "验收示例", 100, 100)
        QTest.qWait(250)
        click(app.popup.open_vocabulary_btn)
        assert app.tray._vocabulary_window is book and book.isVisible()
        assert app.popup._vocabulary_window is None
        if app.vocabulary_hotkey.registered:
            alt_digit("2")
            wait_for(lambda: not book.isVisible())
        print("PASS shared: 面板/弹框/托盘使用同一词库,Alt+2可隐藏按钮打开的词库")
        assert len(store.search()) == 1
        print("BLOCKED: " + ", ".join(blocked) + " 被旧实例/其他程序占用,未操控对方实例" if blocked else
              "PASS: 两组真实全局键开关完整通过")
    finally:
        app.shutdown()
        for window in (app.tray._panel, app.tray._vocabulary_window):
            if window is not None:
                window.close()
        if helper is not None:
            helper.terminate()
            helper.wait(timeout=10)
