"""真实Qt与Win32快捷键验收。隔离词库,不启动鼠标监听或改系统剪贴板。
只关闭本脚本自己创建的窗口/辅助进程,不终止用户实例。
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

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QMessageBox

OUTPUT = ROOT / "artifacts" / "verification" / "vocabulary-hotkey"
OUTPUT.mkdir(parents=True, exist_ok=True)

if "--helper" in sys.argv:
    qapp = QApplication([])
    window = QWidget()
    window.setWindowTitle("TranslateAssistant Hotkey Verification External Window")
    window.resize(450, 200)
    layout = QVBoxLayout(window)
    layout.addWidget(QLabel("独立进程窗口: 验证 Alt+1 全局打开翻译面板"))
    window.show()
    sys.exit(qapp.exec_())

if "--reopen" in sys.argv:
    from vocabulary_store import VocabularyStore
    from vocabulary_ui import VocabularyWindow
    qapp = QApplication([])
    store = VocabularyStore(sys.argv[-1])
    window = VocabularyWindow(store)
    window.present()
    QTest.qWait(300)
    assert window.word_list.count() == 2
    assert "时间" in str(store.search())
    window.grab().save(str(OUTPUT / "wordbook_reopened.png"))
    print("PASS reopen: 新进程词库仍有2个单词与完整释义")
    window.close()
    sys.exit(0)

import win32api
import win32con
import win32gui
import win32process
from main import TranslateApp
from vocabulary_store import VocabularyStore
from global_hotkey import GlobalHotkey

TEMP_ROOT = ROOT / "artifacts" / "test-temp"
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
helper = None


def wait_for(predicate, seconds=45):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QTest.qWait(50)
        if predicate():
            QTest.qWait(200)
            return
    raise RuntimeError("界面验证等待超时")


def external_window(pid):
    found = []
    def visit(hwnd, _):
        if win32gui.IsWindowVisible(hwnd) and win32process.GetWindowThreadProcessId(hwnd)[1] == pid:
            found.append(hwnd)
    win32gui.EnumWindows(visit, None)
    return found[0] if found else None


def activate_external(hwnd):
    # Alt松开使本验证进程可请求前台切换; 只操作自己创建的外部窗口。
    win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
    win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(hwnd)
    QTest.qWait(200)
    assert win32gui.GetForegroundWindow() == hwnd


def alt_one():
    try:
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        win32api.keybd_event(ord("1"), 0, 0, 0)
        QTest.qWait(100)
    finally:
        win32api.keybd_event(ord("1"), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
    QTest.qWait(300)


def translate(panel, text):
    panel.present()
    panel.input_edit.setPlainText(text)
    QTest.mouseClick(panel.translate_btn, Qt.LeftButton)
    wait_for(lambda: not panel._busy)
    assert panel.result_edit.toPlainText() and "失败" not in panel.status.text(), panel.status.text()
    QTest.qWait(1100)


with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as tmp:
    database = Path(tmp) / "verification.db"
    store = VocabularyStore(database)
    app = TranslateApp(vocabulary=store)
    try:
        assert app.hotkey.registered, app.hotkey.error
        helper = subprocess.Popen([sys.executable, __file__, "--helper"])
        wait_for(lambda: external_window(helper.pid) is not None, 10)
        hwnd = external_window(helper.pid)
        activate_external(hwnd)
        alt_one()
        panel = app.tray._panel
        assert panel is not None and panel.isVisible()
        assert win32gui.GetForegroundWindow() == int(panel.winId())
        assert panel.input_edit.hasFocus()
        print("PASS hotkey: 外部进程为前台时Alt+1唤起面板并聚焦输入")

        translate(panel, "time")
        assert "n." in panel.result_edit.toPlainText()
        QTest.mouseClick(panel.save_word_btn, Qt.LeftButton)
        assert "已加入" in panel.save_word_btn.text()
        QTest.mouseClick(panel.save_word_btn, Qt.LeftButton)
        assert panel.save_word_btn.text() == "已在词库"
        assert len(store.search()) == 1
        panel.grab().save(str(OUTPUT / "panel_word_saved.png"))
        print("PASS save: 单词time的词性释义已保存,重复收藏不增加记录")

        QTest.mouseClick(panel.vocabulary_btn, Qt.LeftButton)
        book = app.tray._vocabulary_window
        assert book.word_list.count() == 1
        assert "n." in book.detail_edit.toPlainText()
        book.grab().save(str(OUTPUT / "wordbook.png"))
        book.search_edit.setText("时间")
        assert book.word_list.count() == 1
        book.search_edit.setText("not-a-matching-word")
        assert book.word_list.count() == 0
        book.search_edit.clear()
        book.hide()
        print("PASS wordbook: 面板打开词库,完整释义可见,单词/释义搜索生效")

        translate(panel, "word")
        original_path = store.path
        store.path = Path(tmp)  # 目录不能作为数据库文件,验证真实保存失败的UI反馈。
        QTest.mouseClick(panel.save_word_btn, Qt.LeftButton)
        assert "保存失败" in panel.save_word_btn.text()
        store.path = original_path
        QTest.mouseClick(panel.save_word_btn, Qt.LeftButton)
        assert len(store.search()) == 2
        print("PASS probe: 写入失败显示重试,修复路径后可正常保存")

        content = panel.input_edit.toPlainText()
        panel.showMinimized()
        activate_external(hwnd)
        alt_one()
        assert app.tray._panel is panel and not panel.isMinimized()
        assert panel.input_edit.toPlainText() == content
        assert panel.input_edit.hasFocus()
        print("PASS restore: Alt+1恢复最小化面板,不重复创建或清空内容")

        # 从取词成功信号进入真实后台翻译/弹框,不模拟系统鼠标提取。
        panel.hide()
        app.monitor.text_selected.emit("expect", 100, 100)
        wait_for(lambda: not app._translating)
        assert app.popup.isVisible() and app.popup.save_word_btn.isVisible()
        QTest.mouseClick(app.popup.save_word_btn, Qt.LeftButton)
        assert len(store.search()) == 3
        app.popup.grab().save(str(OUTPUT / "popup_word_saved.png"))
        app.popup.hide_popup()
        print("PASS popup: 划词成功后的expect弹框可收藏词性与释义")

        panel.present()
        translate(panel, "The meeting will\nstart tomorrow at nine.")
        assert not panel.save_word_btn.isEnabled()
        assert panel.result_edit.toPlainText() == "会议将于明天九点开始。"
        print("PASS probe: 句子无收藏按钮,跨行句子翻译没有回归")

        # 真正异步期间修改输入,旧结果不得显示/收藏为新词。
        panel.input_edit.setPlainText("time")
        QTest.mouseClick(panel.translate_btn, Qt.LeftButton)
        panel.input_edit.setPlainText("different")
        wait_for(lambda: not panel._busy)
        assert not panel.result_edit.toPlainText() and not panel.save_word_btn.isEnabled()
        print("PASS probe: 翻译期间改词,迟到结果被丢弃,不误收藏")

        # 删除确认对话框: 仅删除隔离库测试词expect。
        book.present()
        book.search_edit.setText("expect")
        assert book.word_list.count() == 1
        def confirm_delete():
            modal = QApplication.activeModalWidget()
            assert isinstance(modal, QMessageBox)
            QTest.mouseClick(modal.button(QMessageBox.Yes), Qt.LeftButton)
        QTimer.singleShot(200, confirm_delete)
        QTest.mouseClick(book.delete_btn, Qt.LeftButton)
        assert len(store.search()) == 2
        print("PASS delete: 删除前二次确认,仅删选中隔离测试词")
        book.close()
        panel.close()

        competing = GlobalHotkey(app.app)
        assert not competing.start() and competing.error
        app.hotkey.stop()
        assert competing.start()
        competing.stop()
        print("PASS lifecycle: 被占用时注册失败,原实例释放后可再次注册")
        app.shutdown()

        reopened = subprocess.run([sys.executable, __file__, "--reopen", str(database)],
                                  capture_output=True, text=True, encoding="utf-8", timeout=20)
        print(reopened.stdout.strip())
        if reopened.returncode:
            raise RuntimeError(reopened.stderr)
        print("PASS: 词库与真实全局Alt+1完整验收")
    finally:
        app.shutdown()
        if app.tray._panel is not None:
            app.tray._panel.close()
        if app.tray._vocabulary_window is not None:
            app.tray._vocabulary_window.close()
        if helper is not None:
            helper.terminate()
            helper.wait(timeout=10)
