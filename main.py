"""
翻译助手 - 主入口
选中文本后自动弹出翻译气泡，支持英文↔汉语互相翻译 + 朗读 + 复制
全 Qt 主线程架构，Python 3.14 稳定运行
"""
import sys
import os
import signal
from concurrent.futures import ThreadPoolExecutor

# 忽略 Ctrl+C → 防止 keybd_event 模拟的系统按键被终端误判为 SIGINT
try:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
except Exception:
    pass

from python_runtime import check_python_runtime
check_python_runtime()

import logging

from logging_setup import install_all as install_logging

# 先装日志: 之后任何 Qt 插件/代理/网络错误, 即使没有控制台也有据可查
LOG_PATH = install_logging()
logger = logging.getLogger("app")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal, Qt

import win32api
import win32event
import winerror

import config
from translator.factory import create_translator
from translator.word_dict import enrich
from selection_monitor import SelectionMonitor
from popup_ui import TranslatePopup
from tray_manager import TrayManager
from vocabulary_store import VocabularyStore
from global_hotkey import GlobalHotkey, _VOCABULARY_HOTKEY_ID
from qt_runtime import configure_qt_runtime


class TranslateApp(QObject):
    """应用程序主控制器 (QObject, 拥有信号)"""

    # 信号: 从工作线程安全地通知主线程
    _translation_done = pyqtSignal(str, str, str, int, int)  # orig, trans, name, x, y
    _translation_error = pyqtSignal(str, str, int, int)      # text, error, x, y
    _translation_finished = pyqtSignal()                     # 翻译流程结束

    def __init__(self, vocabulary=None):
        super().__init__()
        configure_qt_runtime()
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        self.app.setApplicationName("翻译助手")

        # 线程池 (1 线程)
        self._executor = ThreadPoolExecutor(max_workers=1)

        # 翻译器
        self.translator = create_translator()

        # UI
        self.vocabulary = vocabulary if vocabulary is not None else VocabularyStore()
        self.popup = TranslatePopup(on_deactivate=self._on_popup_hidden, vocabulary=self.vocabulary,
                                    on_open_vocabulary=self._open_vocabulary)

        # 选择监听
        self.monitor = SelectionMonitor()
        self.monitor.text_selected.connect(self._on_text_selected)

        # 系统托盘
        self.tray = TrayManager(self.app, self.monitor, on_quit=self.shutdown,
                                vocabulary=self.vocabulary)
        self.hotkey = GlobalHotkey(self.app)
        self.hotkey.activated.connect(self._toggle_panel, Qt.QueuedConnection)
        self.vocabulary_hotkey = GlobalHotkey(self.app, ord("2"), _VOCABULARY_HOTKEY_ID)
        self.vocabulary_hotkey.activated.connect(self._toggle_vocabulary, Qt.QueuedConnection)
        errors = []
        for hotkey in (self.hotkey, self.vocabulary_hotkey):
            if not hotkey.start():
                errors.append(hotkey.error)
        if errors:
            self.tray.show_message("快捷键不可用", "；".join(errors) + "。可从托盘打开窗口。")

        # 翻译结果信号 → 主线程处理
        self._translation_done.connect(self._show_result)
        self._translation_error.connect(self._show_error)
        self._translation_finished.connect(self._on_translate_done)

        # 状态
        self._translating = False

    # ── 选中文本 → 翻译 ─────────────────────────────────────

    def _on_text_selected(self, text: str, mouse_x: int, mouse_y: int):
        """收到选中文本信号 (主线程)"""
        if self._translating:
            return
        if self.popup.isVisible():
            self.popup.hide_popup()

        self.popup.show_loading(text, mouse_x, mouse_y)
        self._translating = True
        self.monitor.set_busy(True)

        # 线程池执行翻译
        self._executor.submit(self._do_translate, text, mouse_x, mouse_y)

    def _do_translate(self, text: str, mouse_x: int, mouse_y: int):
        """后台执行翻译 (线程池线程)"""
        try:
            result = self.translator.translate(text, "auto")
            # 单词补充词性与多种词义(百度词典), 句子原样直通
            display = enrich(result["original"], result["translated"])
            # 用信号发回主线程 (跨线程安全, Qt 自动排队)
            self._translation_done.emit(
                result["original"], display,
                self.translator.name(), mouse_x, mouse_y
            )
        except Exception as e:
            self._translation_error.emit(text, str(e), mouse_x, mouse_y)
        finally:
            self._translation_finished.emit()

    def _show_result(self, original, translated, translator_name, mx, my):
        self.popup.show_result(original, translated, translator_name, mx, my)

    def _show_error(self, text, error, mx, my):
        self.popup.show_error(text, error, mx, my)

    def _on_translate_done(self):
        self._translating = False
        self.monitor.set_busy(False)

    def _on_popup_hidden(self):
        self.monitor.set_ignore_window(0.5)

    def _open_panel(self):
        self.popup.hide_popup()
        self.tray._on_show_panel()

    def _open_vocabulary(self):
        self.popup.hide_popup()
        self.tray._on_show_vocabulary()

    def _toggle_panel(self):
        self.popup.hide_popup()
        self.tray.toggle_panel()

    def _toggle_vocabulary(self):
        self.popup.hide_popup()
        self.tray.toggle_vocabulary()

    def start(self):
        self.monitor.start()
        self.tray.show_message("翻译助手", self.tray.start_hint())
        self.app.exec_()

    def shutdown(self):
        self.hotkey.stop()
        self.vocabulary_hotkey.stop()
        self.monitor.stop()
        self._executor.shutdown(wait=False, cancel_futures=True)
        self.popup.hide()
        self.tray.hide()


def _hide_own_console():
    """用 python.exe 启动时会带一个黑色控制台; 只在这个控制台专属于本进程时才隐藏,
    避免把用户自己的 cmd/终端窗口藏起来"""
    try:
        import win32console
        import win32gui
        hwnd = win32console.GetConsoleWindow()
        if hwnd and len(win32console.GetConsoleProcessList()) == 1:
            win32gui.ShowWindow(hwnd, 0)  # SW_HIDE
    except Exception:
        pass


def _acquire_single_instance():
    """命名互斥体: 已有实例在运行则返回 None"""
    mutex = win32event.CreateMutex(None, False, "Global\\TranslateAssistant_SingleInstance")
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        return None
    return mutex


def main():
    _hide_own_console()
    logger.info("启动 | 日志: %s", LOG_PATH)
    mutex = _acquire_single_instance()
    if mutex is None:
        logger.warning("已有实例在运行, 本次启动退出")
        return  # 已在托盘运行, 直接退出
    os.environ["QT_QPA_PLATFORM"] = "windows"  # 强制 Windows 原生后端
    app_wrapper = TranslateApp()
    app_wrapper.start()
    logger.info("正常退出")
    # 退出后直接结束进程: 翻译线程可能还卡在网络请求里, 不强退的话进程会在后台挂着
    os._exit(0)


if __name__ == "__main__":
    main()
