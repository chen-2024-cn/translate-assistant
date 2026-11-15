"""词库与实际键盘焦点验收: 隔离数据库,真实全局键盘/鼠标事件。
不关闭用户旧实例。监控在自己界面时开启;外部系统复制不运行以保护剪贴板格式。
"""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from PyQt5.QtCore import QPoint
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication
import win32api
import win32con
import win32gui
import win32process
from main import TranslateApp
from vocabulary_store import VocabularyStore

OUTPUT = ROOT / "artifacts" / "verification" / "input-collection"
OUTPUT.mkdir(parents=True, exist_ok=True)
TEMP = ROOT / "artifacts" / "test-temp"
TEMP.mkdir(parents=True, exist_ok=True)


def wait_for(condition, seconds=40):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        QTest.qWait(30)
        if condition():
            return
    raise RuntimeError("界面操作未达到预期")


def real_click(widget, local=None):
    QTest.qWait(250)  # 等待Qt布局和原生窗口显示完成,否则采集到旧按钮坐标。
    point = widget.mapToGlobal(local or widget.rect().center())
    win32api.SetCursorPos((point.x(), point.y()))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
    QTest.qWait(90)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
    QTest.qWait(180)


def type_ascii(text):
    # SendInput Unicode字符投递到真实前台焦点,不指定控件/窗口。
    # 避免当前中文IME把字母留在预编辑区,导致toPlainText为空的验证误判。
    import ctypes
    from ctypes import wintypes
    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ctypes.c_size_t)]
    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]
    class INPUTUNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]
    class INPUT(ctypes.Structure):
        _anonymous_ = ("data",)
        _fields_ = [("type", wintypes.DWORD), ("data", INPUTUNION)]
    for char in text:
        events = (INPUT * 2)()
        for index, flags in enumerate((4, 4 | 2)):
            events[index].type = 1
            events[index].ki = KEYBDINPUT(0, ord(char), flags, 0, 0)
        assert ctypes.windll.user32.SendInput(2, events, ctypes.sizeof(INPUT)) == 2
        QTest.qWait(15)


def alt_one():
    win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
    win32api.keybd_event(ord("1"), 0, 0, 0)
    QTest.qWait(80)
    win32api.keybd_event(ord("1"), 0, win32con.KEYEVENTF_KEYUP, 0)
    win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
    QTest.qWait(25)


with tempfile.TemporaryDirectory(dir=TEMP) as tmp:
    store = VocabularyStore(Path(tmp) / "words.db")
    app = TranslateApp(vocabulary=store)
    helper = None
    try:
        print("Global Alt+1 registered:", app.hotkey.registered, app.hotkey.error)
        # 真正点击托盘上下文菜单选项(仅菜单显示由工具发起)。
        app.tray._menu.popup(QPoint(150, 150))
        QTest.qWait(120)
        real_click(app.tray._menu, app.tray._menu.actionGeometry(app.tray.show_action).center())
        wait_for(lambda: app.tray._panel is not None and app.tray._panel.isActiveWindow())
        panel = app.tray._panel
        QTest.qWait(150)
        print("Focus evidence:", panel.isActiveWindow(), panel.input_edit.hasFocus(),
              panel._focus_requested, win32gui.GetForegroundWindow(), int(panel.winId()))
        type_ascii("time")
        print("Keyboard evidence:", repr(panel.input_edit.toPlainText()))
        assert panel.input_edit.toPlainText() == "time", panel.input_edit.toPlainText()
        print("PASS tray typing: 菜单打开后没有点击输入框,直接输入time")
        real_click(panel.translate_btn)
        wait_for(lambda: not panel._busy)
        assert panel.result_edit.toPlainText() and panel.save_word_btn.isVisible()
        app.monitor.start()
        real_click(panel.save_word_btn)
        QTest.qWait(600)
        app.monitor.stop()
        assert len(store.search()) == 1 and store.search()[0]["word"] == "time"
        assert "time 已加入" in panel.status.text()
        print("PASS collection: 真实鼠标收藏time,监控开启,可见状态确认写入")
        panel.grab().save(str(OUTPUT / "panel_saved.png"))
        real_click(panel.vocabulary_btn)
        book = app.tray._vocabulary_window
        assert book.word_list.item(0).text() == "time"
        assert "中文释义" in book.detail_edit.toPlainText()
        print("PASS english list: 列表time,详情为中文词性释义")
        book.hide()

        # 模拟旧中文记录,仅写隔离DB,不触及正式词库。
        with closing(sqlite3.connect(store.path)) as db, db:
            db.execute("INSERT INTO vocabulary VALUES (?,?,?,?,?)",
                       ("收获", "收获", "harvest; gain; result", "百度", "2026-01-01"))
        book.present()
        book.search_edit.setText("harvest")
        assert book.word_list.count() == 1 and book.word_list.item(0).text() == "harvest"
        assert "中文释义:\n收获" in book.detail_edit.toPlainText()
        assert [e for e in store.search() if e["word_key"] == "收获"][0]["word"] == "收获"
        book.grab().save(str(OUTPUT / "english_legacy_list.png"))
        print("PASS legacy: 旧收获记录列表显示harvest,中文释义收获,数据库原记录未变")
        book.hide()
        panel.present()
        # 保存button有边缘标点时的实际收藏,走真实面板翻译。
        panel.input_edit.setPlainText("expect,")
        real_click(panel.translate_btn)
        wait_for(lambda: not panel._busy)
        assert panel.save_word_btn.isVisible()
        app.monitor.start()
        real_click(panel.save_word_btn)
        QTest.qWait(600)
        app.monitor.stop()
        assert store.search("expect")[0]["word"] == "expect"
        print("PASS punctuation: expect, 翻译后收藏为英文expect")
        panel.hide()
        app.monitor.text_selected.emit("obvious", 100, 100)
        wait_for(lambda: not app._translating)
        QTest.qWait(300)
        p = app.popup.save_word_btn.mapToGlobal(app.popup.save_word_btn.rect().center())
        h = win32gui.WindowFromPoint((p.x(), p.y()))
        print('Before popup click:', app.popup.isVisible(), app.popup.geometry(),
              app.popup.save_word_btn.geometry(), 'hit pid', win32process.GetWindowThreadProcessId(h)[1], 'self', os.getpid())
        app.monitor.start()
        real_click(app.popup.save_word_btn)
        QTest.qWait(600)
        app.monitor.stop()
        assert store.search("obvious")[0]["word"] == "obvious"
        assert "obvious 已加入" in app.popup.translator_label.text()
        app.popup.grab().save(str(OUTPUT / "popup_saved.png"))
        print('Popup evidence:', app.popup.isVisible(), app.popup.geometry(),
              app.popup.open_vocabulary_btn.geometry())
        real_click(app.popup.open_vocabulary_btn)
        QTest.qWait(250)
        assert app.tray._vocabulary_window is book and book.isVisible()
        assert app.popup._vocabulary_window is None
        book.hide()
        print("PASS popup: 真实鼠标收藏obvious,未被自身取词打断,可打开词库确认")

        if app.hotkey.registered:
            helper = subprocess.Popen([sys.executable, str(ROOT / "scripts" / "verify_vocabulary_hotkey.py"), "--helper"])
            handles = []
            def helper_hwnd():
                handles.clear()
                def visit(hwnd, _):
                    if win32gui.IsWindowVisible(hwnd) and win32process.GetWindowThreadProcessId(hwnd)[1] == helper.pid:
                        handles.append(hwnd)
                win32gui.EnumWindows(visit, None)
                return handles[0] if handles else None
            wait_for(helper_hwnd, 10)
            hwnd = helper_hwnd()
            def focus_external():
                app.monitor.stop()
                # 本脚本受控外部窗口的激活,产品不模拟这些Alt键。
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
                win32gui.SetForegroundWindow(hwnd)
                QTest.qWait(100)
                assert win32gui.GetForegroundWindow() == hwnd
            panel.input_edit.setPlainText("oldinput")
            panel.hide()  # Alt+1现在是开关,先隐藏再验证打开后的输入。
            focus_external()
            alt_one()
            type_ascii("fresh")
            assert panel.input_edit.toPlainText() == "fresh", panel.input_edit.toPlainText()
            print("PASS Alt+1 typing: 外部进程切入面板后立即输入fresh替换旧输入")
            panel.showMinimized()
            focus_external()
            alt_one()
            type_ascii("restored")
            assert panel.input_edit.toPlainText() == "restored", panel.input_edit.toPlainText()
            panel.grab().save(str(OUTPUT / "hotkey_direct_input.png"))
            print("PASS minimized typing: 恢复后不点击输入框直接键入restored")
            # 点击词库后,迟到焦点不得把它抢回面板。
            real_click(panel.vocabulary_btn)
            QTest.qWait(900)
            assert book.isActiveWindow()
            print("PASS no focus stealing: 打开词库后没有迟到抢回面板焦点")
        else:
            print("BLOCKED Alt+1 live typing: 已被旧用户实例占用,未发送热键干扰用户实例。请用户退出后重跑。")
        print("PASS observed UI flows; 系统鼠标取词/Ctrl+C未现场操作,避免覆盖用户剪贴板格式")
    finally:
        app.shutdown()
        for widget in (app.tray._panel, app.tray._vocabulary_window, app.popup._vocabulary_window):
            if widget is not None:
                widget.close()
        if helper is not None:
            helper.terminate()
            helper.wait(timeout=10)
