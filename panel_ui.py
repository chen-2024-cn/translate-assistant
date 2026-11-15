"""
独立翻译面板 (托盘菜单 → 打开翻译面板)
窗口可自由缩放, 原文/译文区域可滚动、可选择, 翻译在后台线程执行
"""
import threading
import time

import win32api
import win32con
import win32gui

import pyperclip
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QSplitter, QCheckBox, QShortcut, QApplication,
)

import config
from tts_engine import TTSEngine
from vocabulary_store import VocabularyStore
from vocabulary_ui import VocabularySaveButton, VocabularyWindow

STYLE = """
QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-size: 18px;
}
QTextEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 8px;
    padding: 12px;
    font-size: 24px;
    selection-background-color: #585b70;
}
#ResultEdit {
    color: #a6e3a1;
}
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 10px 26px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
    color: #89b4fa;
}
QPushButton:disabled {
    color: #6c7086;
}
#SmallBtn {
    padding: 4px 16px;
    font-size: 16px;
}
#SectionLabel {
    color: #6c7086;
    font-size: 16px;
}
QSplitter::handle {
    background-color: #45475a;
    height: 3px;
    margin: 3px 40px;
    border-radius: 1px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
}
"""


class TranslatePanel(QWidget):
    _done = pyqtSignal(str, str, str, int)   # 原文, 译文, 引擎名, 输入版本
    _failed = pyqtSignal(str, int)

    def __init__(self, vocabulary=None, on_open_vocabulary=None):
        super().__init__(None)
        self._busy = False
        self._translator = None
        self._revision = 0
        self._focus_requested = False
        self._focus_deadline = 0
        self._focus_select_all = False
        self._focus_timer = QTimer(self)
        self._focus_timer.setInterval(15)
        self._focus_timer.timeout.connect(self._complete_input_focus)
        self._vocabulary = vocabulary if vocabulary is not None else VocabularyStore()
        self._vocabulary_window = None
        self._open_vocabulary = on_open_vocabulary or self._show_vocabulary

        self.setWindowTitle("翻译助手 - 翻译面板")
        self.resize(940, 720)
        self.setMinimumSize(560, 400)
        self.setStyleSheet(STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("输入文本进行翻译")
        title.setStyleSheet("color: #89b4fa; font-size: 21px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        self.vocabulary_btn = QPushButton("词库")
        self.vocabulary_btn.setCursor(Qt.PointingHandCursor)
        self.vocabulary_btn.clicked.connect(self._open_vocabulary)
        header.addWidget(self.vocabulary_btn)
        self.pin_box = QCheckBox("置顶")
        self.pin_box.toggled.connect(self._on_pin)
        header.addWidget(self.pin_box)
        layout.addLayout(header)

        self.input_edit = QTextEdit()
        self.input_edit.setAcceptRichText(False)
        self.input_edit.setPlaceholderText("在此输入或粘贴要翻译的文本，按 Ctrl+Enter 翻译")

        self.result_edit = QTextEdit()
        self.result_edit.setObjectName("ResultEdit")
        self.result_edit.setReadOnly(True)
        self.result_edit.setPlaceholderText("译文会显示在这里")

        def small_btn(text, slot):
            b = QPushButton(text)
            b.setObjectName("SmallBtn")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(slot)
            return b

        def section(label, edit, *buttons):
            box = QWidget()
            col = QVBoxLayout(box)
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(6)
            head = QHBoxLayout()
            tag = QLabel(label)
            tag.setObjectName("SectionLabel")
            head.addWidget(tag)
            head.addStretch()
            for b in buttons:
                head.addWidget(b)
            col.addLayout(head)
            col.addWidget(edit, 1)
            return box

        self.speak_input_btn = small_btn("🔊 朗读原文", self._speak_input)
        self.speak_result_btn = small_btn("🔊 朗读译文", self._speak_result)
        self.copy_btn = small_btn("复制译文", self._copy)
        self.save_word_btn = VocabularySaveButton(self._vocabulary)
        self.save_word_btn.setObjectName("SmallBtn")
        self.input_edit.textChanged.connect(self._input_changed)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(section("原文", self.input_edit, self.speak_input_btn))
        splitter.addWidget(section("译文", self.result_edit,
                                   self.save_word_btn, self.speak_result_btn, self.copy_btn))
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([280, 320])
        layout.addWidget(splitter, 1)

        buttons = QHBoxLayout()
        self.translate_btn = QPushButton("翻译  (Ctrl+Enter)")
        self.translate_btn.setCursor(Qt.PointingHandCursor)
        self.translate_btn.clicked.connect(self._translate)
        clear_btn = QPushButton("清空")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear)
        stop_btn = QPushButton("停止朗读")
        stop_btn.setCursor(Qt.PointingHandCursor)
        stop_btn.clicked.connect(self._stop_speak)
        buttons.addWidget(self.translate_btn)
        buttons.addWidget(clear_btn)
        buttons.addStretch()
        buttons.addWidget(stop_btn)
        layout.addLayout(buttons)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color: #6c7086; font-size: 15px;")
        layout.addWidget(self.status)

        for key in ("Ctrl+Return", "Ctrl+Enter"):
            QShortcut(QKeySequence(key), self, activated=self._translate)

        self.save_word_btn.feedback.connect(self.status.setText)
        self._done.connect(self._on_done)
        self._failed.connect(self._on_failed)

    def present(self):
        """显示并带到最前; 已经打开时不会重复创建"""
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self._focus_requested = True
        self._focus_select_all = True
        self._focus_deadline = time.monotonic() + 0.8
        self.raise_()
        self.activateWindow()
        try:
            win32gui.SetForegroundWindow(int(self.winId()))
        except win32gui.error:
            pass  # Windows可能限制跨进程激活,不模拟额外按键强抢焦点。
        self._complete_input_focus()
        if self._focus_requested:
            self._focus_timer.start()

    def _complete_input_focus(self):
        if (not self._focus_requested or not self.isVisible()
                or time.monotonic() > self._focus_deadline):
            self._focus_requested = False
            self._focus_timer.stop()
            return
        if not self.isActiveWindow() or QApplication.activePopupWidget() is not None:
            return
        self.input_edit.setFocus(Qt.ActiveWindowFocusReason)
        try:
            if win32gui.GetForegroundWindow() == int(self.winId()):
                win32gui.SetFocus(int(self.input_edit.winId()))
        except win32gui.error:
            pass
        if self._focus_select_all:
            self.input_edit.selectAll()
            self._focus_select_all = False
        # Alt释放后再次确认焦点,避免系统处理Alt菜单状态时覆盖输入焦点。
        if not (win32api.GetAsyncKeyState(win32con.VK_MENU) & 0x8000):
            self._focus_requested = False
            self._focus_timer.stop()

    def event(self, event):
        if event.type() in (QEvent.WindowDeactivate, QEvent.Hide):
            if hasattr(self, "_focus_timer"):
                self._focus_requested = False
                self._focus_timer.stop()
        elif event.type() == QEvent.WindowActivate and getattr(self, "_focus_requested", False):
            QTimer.singleShot(0, self._complete_input_focus)
        return super().event(event)

    def _show_vocabulary(self):
        if self._vocabulary_window is None:
            self._vocabulary_window = VocabularyWindow(self._vocabulary)
        self._vocabulary_window.present()

    def _input_changed(self):
        self._revision += 1
        self.save_word_btn.clear_result()
        self.result_edit.clear()

    def _on_pin(self, on: bool):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        self.show()

    def _clear(self):
        self._revision += 1
        self.save_word_btn.clear_result()
        self.input_edit.clear()
        self.result_edit.clear()
        self.status.setText("")
        self.input_edit.setFocus()

    def _copy(self):
        text = self.result_edit.toPlainText()
        if not text:
            return
        pyperclip.copy(text)
        self.copy_btn.setText("✓ 已复制")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("复制译文"))

    def _speak(self, text: str, btn: QPushButton, idle_text: str):
        if not text.strip():
            return
        TTSEngine().speak(text)
        btn.setText("▶ 朗读中...")
        QTimer.singleShot(1500, lambda: btn.setText(idle_text))

    def _speak_input(self):
        self._speak(self.input_edit.toPlainText(), self.speak_input_btn, "🔊 朗读原文")

    def _speak_result(self):
        self._speak(self.result_edit.toPlainText(), self.speak_result_btn, "🔊 朗读译文")

    def _stop_speak(self):
        TTSEngine().stop()

    def _translate(self):
        text = self.input_edit.toPlainText().strip()
        if not text or self._busy:
            return
        note = ""
        if len(text) > config.MAX_TEXT_LENGTH:
            text = text[: config.MAX_TEXT_LENGTH]
            note = f"（原文过长，只翻译了前 {config.MAX_TEXT_LENGTH} 个字符）"

        self._busy = True
        self.translate_btn.setEnabled(False)
        self.translate_btn.setText("翻译中...")
        self.status.setStyleSheet("color: #6c7086; font-size: 15px;")
        self.status.setText(note)
        self.save_word_btn.clear_result()
        threading.Thread(target=self._work, args=(text, self._revision), daemon=True).start()

    def _work(self, text: str, revision: int):
        try:
            if self._translator is None:
                from translator.factory import create_translator
                self._translator = create_translator()
            result = self._translator.translate(text, "auto")
            from translator.word_dict import enrich
            display = enrich(result["original"], result["translated"])
            self._done.emit(result["original"], display, self._translator.name(), revision)
        except Exception as e:
            self._failed.emit(str(e), revision)

    def _finish(self):
        self._busy = False
        self.translate_btn.setEnabled(True)
        self.translate_btn.setText("翻译  (Ctrl+Enter)")

    def _on_done(self, original: str, translated: str, engine: str, revision: int):
        self._finish()
        if revision != self._revision:
            return
        self.result_edit.setPlainText(translated)
        self.save_word_btn.set_result(original, translated, engine)
        self.status.setText(f"{self.status.text()} — {engine}".strip())

    def _on_failed(self, error: str, revision: int):
        self._finish()
        if revision != self._revision:
            return
        self.save_word_btn.clear_result()
        self.status.setStyleSheet("color: #f38ba8; font-size: 15px;")
        self.status.setText(f"翻译失败: {error}")
