"""
系统托盘模块
提供最小化到托盘、右键菜单（退出）、双击还原等功能
"""
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QActionGroup, QApplication
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt5.QtCore import Qt, QTimer

import settings
from vocabulary_store import VocabularyStore
from vocabulary_ui import VocabularyWindow


def _create_tray_icon() -> QIcon:
    """动态生成一个简单的翻译图标 (地球+T)"""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # 圆形背景
    painter.setBrush(QColor("#89b4fa"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(1, 1, 30, 30)

    # T 字母
    painter.setPen(QColor("#1e1e2e"))
    font = painter.font()
    font.setPixelSize(18)
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "T")

    painter.end()
    return QIcon(pixmap)


class TrayManager:
    """系统托盘管理"""

    def __init__(self, app: QApplication, monitor, on_quit=None, vocabulary=None):
        self.app = app
        self.monitor = monitor
        self.on_quit = on_quit
        self._panel = None
        self._vocabulary = vocabulary if vocabulary is not None else VocabularyStore()
        self._vocabulary_window = None
        self._tray = QSystemTrayIcon()
        self._tray.setIcon(_create_tray_icon())

        # 右键菜单 (成员变量持有引用, 避免被回收)
        self._menu = QMenu()
        menu = self._menu

        self.show_action = QAction("📋 打开翻译面板 (Alt+1)")
        self.show_action.triggered.connect(lambda: QTimer.singleShot(0, self._on_show_panel))
        menu.addAction(self.show_action)
        self.vocabulary_action = QAction("📖 打开词库 (Alt+2)", menu)
        self.vocabulary_action.triggered.connect(lambda: QTimer.singleShot(0, self._on_show_vocabulary))
        menu.addAction(self.vocabulary_action)

        menu.addSeparator()

        # 划词翻译总开关
        self.enable_action = QAction("划词翻译")
        self.enable_action.setCheckable(True)
        self.enable_action.setChecked(self.monitor.enabled)
        self.enable_action.toggled.connect(self._on_toggle_enabled)
        menu.addAction(self.enable_action)

        # 触发方式 (二选一)
        mode_group = QActionGroup(menu)
        mode_group.setExclusive(True)
        self.ctrl_action = QAction("按住 Ctrl 再选中才翻译")
        self.auto_action = QAction("选中即译 (自动忽略代码)")
        for action, mode in ((self.ctrl_action, settings.MODE_CTRL),
                             (self.auto_action, settings.MODE_AUTO)):
            action.setCheckable(True)
            action.setChecked(self.monitor.trigger_mode == mode)
            action.triggered.connect(lambda _checked, m=mode: self._on_mode(m))
            mode_group.addAction(action)
            menu.addAction(action)

        menu.addSeparator()

        # 必须保存为成员变量: QAction 没有父对象时, 局部变量被回收会连带从菜单里消失
        self.quit_action = QAction("❌ 退出", menu)
        self.quit_action.triggered.connect(self._on_quit)
        menu.addAction(self.quit_action)

        self._tray.setContextMenu(menu)
        self._refresh_tooltip()

        # 双击打开面板
        self._tray.activated.connect(self._on_activated)

        self._tray.show()

    def start_hint(self) -> str:
        if self.monitor.trigger_mode == settings.MODE_CTRL:
            return "已启动，按住 Ctrl 再选中文字即可翻译。右键托盘图标可切换。"
        return "已启动，选中文字即自动翻译。右键托盘图标可切换。"

    def _refresh_tooltip(self):
        if not self.monitor.enabled:
            self._tray.setToolTip("翻译助手 - 划词翻译已关闭")
        elif self.monitor.trigger_mode == settings.MODE_CTRL:
            self._tray.setToolTip("翻译助手 - 按住 Ctrl 选中文字翻译")
        else:
            self._tray.setToolTip("翻译助手 - 选中即译")

    def _on_toggle_enabled(self, checked: bool):
        self.monitor.set_enabled(checked)
        self._refresh_tooltip()

    def _on_mode(self, mode: str):
        self.monitor.set_trigger_mode(mode)
        self._refresh_tooltip()

    def _on_activated(self, reason):
        """托盘图标激活回调"""
        if reason == QSystemTrayIcon.DoubleClick:
            QTimer.singleShot(0, self._on_show_panel)

    def _on_show_panel(self):
        """打开独立翻译面板 (只创建一次, 再次点击直接带到最前)"""
        if self._panel is None:
            from panel_ui import TranslatePanel
            self._panel = TranslatePanel(self._vocabulary, self._on_show_vocabulary)
        self._panel.present()

    def _on_show_vocabulary(self):
        if self._vocabulary_window is None:
            self._vocabulary_window = VocabularyWindow(self._vocabulary)
        self._vocabulary_window.present()

    def toggle_panel(self):
        """快捷键切换可见性; 最小化视为需要恢复,不清空内容。"""
        if QApplication.activeModalWidget() is not None:
            return
        if self._panel is not None and self._panel.isVisible() and not self._panel.isMinimized():
            self._panel.hide()
        else:
            self._on_show_panel()

    def toggle_vocabulary(self):
        if QApplication.activeModalWidget() is not None:
            return
        window = self._vocabulary_window
        if window is not None and window.isVisible() and not window.isMinimized():
            window.hide()
        else:
            self._on_show_vocabulary()

    def hide(self):
        """退出时移除托盘图标, 避免残留幽灵图标"""
        self._tray.hide()

    def _on_quit(self):
        """退出应用"""
        if self.on_quit:
            self.on_quit()
        self.app.quit()

    def show_message(self, title: str, msg: str):
        """显示托盘气泡消息"""
        self._tray.showMessage(title, msg, QSystemTrayIcon.Information, 2000)
