"""
翻译弹窗 UI
无边框悬浮窗，显示在鼠标附近，包含原文、译文、复制和朗读按钮

原文/译文区为只读可滚动 QTextEdit:
  - 长原文在自己的小区域内滚动(上限84px), 不再挤占/覆盖译文
  - 译文区高度随内容自适应, 上限 config.POPUP_MAX_HEIGHT, 超出内部滚动
  - 译文字号 18px(原文 15px), 比旧版(14px/13px)明显放大
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QApplication, QTextEdit
)
from PyQt5.QtCore import Qt, QPoint, QTimer, QPropertyAnimation, QEasingCurve, QEvent

import config
from tts_engine import TTSEngine
from vocabulary_store import VocabularyStore
from vocabulary_ui import VocabularySaveButton, VocabularyWindow

import win32api
import win32con


STYLE = """
/* 主窗口 */
#PopupWindow {
    background-color: #1e1e2e;
    border: 1px solid #45475a;
    border-radius: 12px;
}

/* 原文区 */
#OriginEdit {
    color: #cdd6f4;
    font-size: 15px;
    background-color: #313244;
    border: none;
    border-radius: 8px;
    padding: 6px 10px;
    selection-background-color: #585b70;
}

/* 分隔线 */
#SeparatorLine {
    background-color: #45475a;
    max-height: 1px;
    margin: 4px 8px;
}

/* 译文区 */
#ResultEdit {
    color: #a6e3a1;
    font-size: 18px;
    font-weight: bold;
    background-color: #313244;
    border: none;
    border-radius: 8px;
    padding: 8px 10px;
    selection-background-color: #585b70;
}

/* 译者信息 */
#TranslatorLabel {
    color: #6c7086;
    font-size: 10px;
    padding: 0px 12px 4px 12px;
}

/* 底部按钮区 */
QPushButton {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 12px;
}
QPushButton:hover {
    background-color: #45475a;
    border-color: #89b4fa;
    color: #89b4fa;
}
QPushButton:pressed {
    background-color: #585b70;
}
#CopyBtn {
    background-color: #45475a;
}
#CopyBtn:hover {
    background-color: #585b70;
    color: #f9e2af;
    border-color: #f9e2af;
}
#SpeakBtn {
    background-color: #45475a;
}
#SpeakBtn:hover {
    background-color: #585b70;
    color: #a6e3a1;
    border-color: #a6e3a1;
}

/* 细滚动条 */
QScrollBar:vertical {
    width: 8px;
    background: transparent;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #585b70;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
"""

# 边距/边框/内衬/滚动条占用的横向空间 (估算文本换行宽度用)
_H_CHROME = 44


class TranslatePopup(QWidget):
    """翻译结果弹窗"""

    def __init__(self, on_deactivate=None, vocabulary=None, on_open_vocabulary=None):
        super().__init__(None)
        self.on_deactivate = on_deactivate
        self._vocabulary = vocabulary if vocabulary is not None else VocabularyStore()
        self._vocabulary_window = None
        self._on_open_vocabulary = on_open_vocabulary
        self._init_ui()
        self._init_timer()
        self.hide()

    def _init_ui(self):
        """初始化 UI 布局"""
        self.setObjectName("PopupWindow")
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        # 不使用Qt.Popup的鼠标抓取,避免点击收藏后重放点击意外关闭。
        QApplication.instance().installEventFilter(self)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setFixedWidth(config.POPUP_WIDTH)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(4)

        # 原文区 (只读可滚动: 长原文内部滚动, 不再把译文挤出可视区)
        self.origin_edit = self._make_edit("OriginEdit")

        # 分隔线
        sep = QFrame()
        sep.setObjectName("SeparatorLine")
        sep.setFrameShape(QFrame.HLine)

        # 译文区 (只读可滚动: 字号放大, 高度随内容自适应)
        self.translated_edit = self._make_edit("ResultEdit")

        # 加载动画
        self.spinner = QLabel("● ● ●")
        self.spinner.setStyleSheet("""
            QLabel {
                color: #89b4fa;
                font-size: 16px;
                letter-spacing: 4px;
                padding: 10px;
            }
        """)
        self.spinner.setAlignment(Qt.AlignCenter)

        # 翻译来源
        self.translator_label = QLabel("")
        self.translator_label.setObjectName("TranslatorLabel")
        self.translator_label.setAlignment(Qt.AlignRight)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(4, 2, 4, 2)
        btn_layout.setSpacing(8)
        btn_layout.addStretch()

        self.copy_origin_btn = self._make_button("复制原文", "CopyBtn", self._on_copy_origin)
        self.copy_btn = self._make_button("复制译文", "CopyBtn", self._on_copy_translated)
        self.speak_origin_btn = self._make_button("朗读原文", "SpeakBtn", self._on_speak_origin)
        self.speak_btn = self._make_button("朗读译文", "SpeakBtn", self._on_speak_translated)

        for b in (self.copy_origin_btn, self.copy_btn,
                  self.speak_origin_btn, self.speak_btn):
            btn_layout.addWidget(b)

        main_layout.addWidget(self.origin_edit)
        main_layout.addWidget(sep)
        main_layout.addWidget(self.spinner)
        main_layout.addWidget(self.translated_edit)
        main_layout.addWidget(self.translator_label)
        main_layout.addLayout(btn_layout)
        self.save_word_btn = VocabularySaveButton(self._vocabulary)
        main_layout.addWidget(self.save_word_btn)
        self.save_word_btn.feedback.connect(self._show_save_feedback)
        self.open_vocabulary_btn = self._make_button("打开词库", "CopyBtn", self._open_vocabulary)
        main_layout.addWidget(self.open_vocabulary_btn)

        self.setStyleSheet(STYLE)

        # 数据
        self._original_text = ""
        self._translated_text = ""

    @staticmethod
    def _make_edit(object_name: str) -> QTextEdit:
        e = QTextEdit()
        e.setObjectName(object_name)
        e.setReadOnly(True)
        e.setAcceptRichText(False)
        e.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return e

    @staticmethod
    def _make_button(text: str, object_name: str, slot) -> QPushButton:
        b = QPushButton(text)
        b.setObjectName(object_name)
        b.setCursor(Qt.PointingHandCursor)
        b.clicked.connect(slot)
        return b

    def _init_timer(self):
        """初始化自动隐藏计时器"""
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_popup)
        self._outside_click_timer = QTimer(self)
        self._outside_click_timer.setInterval(40)
        self._outside_click_timer.timeout.connect(self._check_outside_click)
        self._mouse_pressed = False

    def _fit_edit(self, edit: QTextEdit, cap: int, minimum: int = 40):
        """高度随内容自适应; 超过 cap 时内部滚动 (修复长文本译文被截断看不见)"""
        doc = edit.document()
        doc.setTextWidth(max(config.POPUP_WIDTH - _H_CHROME, 80))
        h = int(doc.size().height()) + 18   # 18 = 上下内衬 + 余量
        edit.setFixedHeight(max(minimum, min(h, cap)))

    def show_loading(self, text: str, mouse_x: int, mouse_y: int):
        """显示加载中状态"""
        self._original_text = text
        self._translated_text = ""
        self.save_word_btn.clear_result()

        self.origin_edit.setPlainText(text)
        self._fit_edit(self.origin_edit, cap=84)
        self.spinner.setVisible(True)
        self.translated_edit.setVisible(False)
        self.translator_label.setText("")
        self.copy_btn.setVisible(False)
        self.copy_origin_btn.setVisible(True)
        self.speak_btn.setVisible(False)
        self.speak_origin_btn.setVisible(True)

        self._position_near_cursor(mouse_x, mouse_y)
        self._show_with_fade()
        self._hide_timer.stop()

    def show_result(self, original: str, translated: str, translator_name: str,
                    mouse_x: int, mouse_y: int):
        """显示翻译结果"""
        self._original_text = original
        self._translated_text = translated
        self.save_word_btn.set_result(original, translated, translator_name)

        self.origin_edit.setPlainText(original)
        self._fit_edit(self.origin_edit, cap=84)
        self.spinner.setVisible(False)
        self.translated_edit.setStyleSheet("")   # 清除可能残留的错误态样式
        self.translated_edit.setPlainText(translated)
        self._fit_edit(self.translated_edit, cap=config.POPUP_MAX_HEIGHT)
        self.translated_edit.setVisible(True)
        self.translator_label.setText(f"— {translator_name}")
        for b in (self.copy_btn, self.copy_origin_btn,
                  self.speak_btn, self.speak_origin_btn):
            b.setVisible(True)
            b.setEnabled(True)

        self._position_near_cursor(mouse_x, mouse_y)
        self._show_with_fade()

        # 自动隐藏 (如果配置了)
        if config.POPUP_DURATION > 0:
            self._hide_timer.start(int(config.POPUP_DURATION * 1000))

    def show_error(self, text: str, error: str, mouse_x: int, mouse_y: int):
        """显示错误信息"""
        self._original_text = text
        self._translated_text = ""
        self.save_word_btn.clear_result()

        self.origin_edit.setPlainText(text)
        self._fit_edit(self.origin_edit, cap=84)
        self.spinner.setVisible(False)
        self.translated_edit.setPlainText(f"❌ {error}")
        self.translated_edit.setStyleSheet(
            "#ResultEdit { color: #f38ba8; font-size: 14px; font-weight: bold;"
            " background-color: #313244; border: none; border-radius: 8px;"
            " padding: 8px 10px; }")
        self._fit_edit(self.translated_edit, cap=200)
        self.translated_edit.setVisible(True)
        self.translator_label.setText("")
        self.copy_btn.setVisible(False)
        self.copy_origin_btn.setVisible(True)
        self.speak_btn.setVisible(False)
        self.speak_origin_btn.setVisible(True)

        self._position_near_cursor(mouse_x, mouse_y)
        self._show_with_fade()

        if config.POPUP_DURATION > 0:
            self._hide_timer.start(int(config.POPUP_DURATION * 1000))

    def _position_near_cursor(self, mouse_x: int, mouse_y: int):
        """将弹窗定位在鼠标附近, 超出屏幕自动换边"""
        screen = QApplication.screenAt(QPoint(mouse_x, mouse_y))
        if screen is None:
            screen = QApplication.primaryScreen()
        screen_geo = screen.availableGeometry()

        self.adjustSize()
        w = self.width()
        h = self.height()

        # 优先在鼠标右下方显示
        x = mouse_x + config.POPUP_OFFSET_X
        y = mouse_y + config.POPUP_OFFSET_Y

        # 超出右/下边界则翻到鼠标另一侧
        if x + w > screen_geo.right():
            x = mouse_x - w - config.POPUP_OFFSET_X
        if y + h > screen_geo.bottom():
            y = mouse_y - h - config.POPUP_OFFSET_Y

        x = max(screen_geo.left(), x)
        y = max(screen_geo.top(), y)
        self.move(x, y)

    def _check_outside_click(self):
        # Tool窗口没有Popup鼠标抓取,仍保留点击其他软件时关闭的原有行为。
        pressed = bool(win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000)
        if pressed and not self._mouse_pressed:
            x, y = win32api.GetCursorPos()
            if not self.frameGeometry().contains(QPoint(x, y)):
                self.hide_popup()
        self._mouse_pressed = pressed

    def _show_with_fade(self):
        """带淡入动画显示"""
        self._mouse_pressed = bool(win32api.GetAsyncKeyState(win32con.VK_LBUTTON) & 0x8000)
        self._outside_click_timer.start()
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._fade_in()

    def _fade_in(self):
        """淡入动画"""
        self._anim = QPropertyAnimation(self, b"windowOpacity")
        self._anim.setDuration(150)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(0.96)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.start()

    def eventFilter(self, watched, event):
        if self.isVisible() and event.type() == QEvent.MouseButtonPress:
            if hasattr(event, "globalPos") and not self.frameGeometry().contains(event.globalPos()):
                self.hide_popup()
        return False

    def hideEvent(self, event):
        """窗口隐藏时（PopUp 被点击外部自动触发）清理状态"""
        self.translated_edit.setStyleSheet("")
        if hasattr(self, "_outside_click_timer"):
            self._outside_click_timer.stop()
        if self.on_deactivate:
            self.on_deactivate()
        super().hideEvent(event)

    def hide_popup(self):
        """手动隐藏弹窗"""
        self.hide()

    def _show_save_feedback(self, message):
        # 状态文案变长不能改变弹框宽高/移动按钮,避免下一次点击落到窗外。
        self.translator_label.setToolTip(message)
        metrics = self.translator_label.fontMetrics()
        self.translator_label.setText(metrics.elidedText(message, Qt.ElideRight,
                                                        max(100, self.width() - 48)))

    def _open_vocabulary(self):
        self.hide_popup()
        if self._on_open_vocabulary is not None:
            self._on_open_vocabulary()
            return
        if self._vocabulary_window is None:
            self._vocabulary_window = VocabularyWindow(self._vocabulary)
        self._vocabulary_window.present()

    def _on_copy_origin(self):
        """复制原文"""
        import pyperclip
        pyperclip.copy(self._original_text)
        self.copy_origin_btn.setText("✓ 已复制")
        QTimer.singleShot(1500, lambda: self.copy_origin_btn.setText("复制原文"))

    def _on_copy_translated(self):
        """复制译文"""
        import pyperclip
        pyperclip.copy(self._translated_text)
        self.copy_btn.setText("✓ 已复制")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("复制译文"))

    def _on_speak_origin(self):
        """朗读原文"""
        self.speak_origin_btn.setText("▶ 朗读中...")
        TTSEngine().speak(self._original_text)
        QTimer.singleShot(2000, lambda: self.speak_origin_btn.setText("朗读原文"))

    def _on_speak_translated(self):
        """朗读译文"""
        self.speak_btn.setText("▶ 朗读中...")
        TTSEngine().speak(self._translated_text)
        QTimer.singleShot(2000, lambda: self.speak_btn.setText("朗读译文"))
