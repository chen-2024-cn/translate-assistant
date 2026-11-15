"""词库浏览窗口与复用收藏按钮。只收藏现有翻译结果,不增加网络请求。"""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QTextEdit, QPushButton, QSplitter, QMessageBox, QCheckBox,
)

from vocabulary_entry import english_word, display_entry

import win32gui


class VocabularySaveButton(QPushButton):
    feedback = pyqtSignal(str)

    def __init__(self, store, parent=None):
        super().__init__("加入词库", parent)
        self._store = store
        self._entry = None
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self._save)
        self.clear_result()

    def clear_result(self):
        self._entry = None
        self.setEnabled(False)
        self.hide()
        self.setText("加入词库")
        self.setToolTip("")

    def set_result(self, word: str, meaning: str, engine: str):
        self.clear_result()
        word = english_word(word)
        if word and meaning.strip():
            self._entry = (word, meaning, engine)
            self.setEnabled(True)
            self.show()

    def _save(self):
        if self._entry is None:
            return
        try:
            added = self._store.add(*self._entry)
            self.setText("✓ 已加入词库" if added else "已在词库")
            self.setToolTip("词库已保存,重启后仍保留" if added else "未重复添加或覆盖原有释义")
            self.feedback.emit(f"{self._entry[0]} 已加入词库" if added else
                               f"{self._entry[0]} 已在词库,未重复添加")
        except (RuntimeError, ValueError) as e:
            self.setText("保存失败,点击重试")
            self.setToolTip(str(e))
            self.feedback.emit(f"保存失败: {e}")


class VocabularyWindow(QWidget):
    def __init__(self, store):
        super().__init__(None)
        self._store = store
        self.setWindowTitle("翻译助手 - 词库")
        self.resize(880, 600)
        self.setMinimumSize(560, 400)
        self.setStyleSheet("""
            QWidget { background: #1e1e2e; color: #cdd6f4; font-size: 18px; }
            QLineEdit, QListWidget, QTextEdit {
                background: #313244; border: 1px solid #45475a;
                border-radius: 6px; padding: 8px; selection-background-color: #585b70;
            }
            QTextEdit { color: #a6e3a1; font-size: 22px; }
            QPushButton { background: #313244; border: 1px solid #45475a;
                border-radius: 6px; padding: 8px 16px; }
            QPushButton:hover { color: #89b4fa; }
            QPushButton:disabled { color: #6c7086; }
        """)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("我的词库"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索单词或释义")
        layout.addWidget(self.search_edit)
        self.legacy_box = QCheckBox("查看无法确定英文词头的旧词条")
        self.legacy_box.toggled.connect(self.refresh)
        layout.addWidget(self.legacy_box)
        self.word_list = QListWidget()
        self.detail_edit = QTextEdit()
        self.detail_edit.setReadOnly(True)
        self.detail_edit.setPlaceholderText("选择一个单词查看完整词性与释义")
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.word_list)
        splitter.addWidget(self.detail_edit)
        splitter.setSizes([250, 600])
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)
        bottom = QHBoxLayout()
        self.status = QLabel("")
        self.status.setWordWrap(True)
        bottom.addWidget(self.status, 1)
        self.delete_btn = QPushButton("删除选中词条")
        self.delete_btn.setEnabled(False)
        bottom.addWidget(self.delete_btn)
        layout.addLayout(bottom)
        self.search_edit.textChanged.connect(self.refresh)
        self.word_list.currentItemChanged.connect(self._show_detail)
        self.delete_btn.clicked.connect(self._delete)
        self._store.changed.connect(self.refresh)

    def present(self):
        self.refresh()
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        try:
            win32gui.SetForegroundWindow(int(self.winId()))
        except win32gui.error:
            pass
        self.search_edit.setFocus(Qt.ActiveWindowFocusReason)

    def refresh(self):
        current = self.word_list.currentItem()
        selected = current.data(Qt.UserRole)["word_key"] if current else None
        try:
            entries = [display_entry(entry) for entry in self._store.search()]
            unresolved = [entry for entry in entries if not entry["display_word"]]
            self.legacy_box.setVisible(bool(unresolved))
            words = unresolved if self.legacy_box.isChecked() else [
                entry for entry in entries if entry["display_word"]
            ]
            query = self.search_edit.text().strip().casefold()
            words = [entry for entry in words if query in (
                entry["display_word"] + " " + entry["word"] + " " + entry["meaning"]
            ).casefold()]
        except RuntimeError as e:
            self.status.setText(str(e))
            self.word_list.clear()
            return
        self.word_list.clear()
        for entry in words:
            item = QListWidgetItem(entry["display_word"] or entry["word"])
            if entry["legacy"]:
                item.setToolTip("旧词条按原数据展示,未修改数据库")
            item.setData(Qt.UserRole, entry)
            self.word_list.addItem(item)
            if entry["word_key"] == selected:
                self.word_list.setCurrentItem(item)
        if self.word_list.currentItem() is None and words:
            self.word_list.setCurrentRow(0)
        self.status.setText(f"共 {len(words)} 个词条" if words else
                            ("未找到匹配词条" if self.search_edit.text().strip() else
                             "词库为空,翻译单词后点击‘加入词库’"))

    def _show_detail(self, current, previous=None):
        self.delete_btn.setEnabled(current is not None)
        if current is None:
            self.detail_edit.clear()
            return
        entry = current.data(Qt.UserRole)
        word = entry["display_word"] or "旧词条 (英文词头待确认)"
        extra = f"\n\n旧记录中的英文译词: {entry['meaning']}" if entry["legacy"] else ""
        self.detail_edit.setPlainText(
            f"{word}\n\n中文释义:\n{entry['chinese_meaning']}{extra}\n\n"
            f"来源: {entry['engine']}\n加入时间: {entry['created_at']}"
        )

    def _delete(self):
        current = self.word_list.currentItem()
        if current is None:
            return
        entry = current.data(Qt.UserRole)
        answer = QMessageBox.question(self, "删除词条", f"确认从词库删除 ‘{entry['word']}’ 吗?",
                                      QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if answer != QMessageBox.Yes:
            return
        try:
            self._store.remove(entry["word_key"])
        except RuntimeError as e:
            self.status.setText(str(e))
