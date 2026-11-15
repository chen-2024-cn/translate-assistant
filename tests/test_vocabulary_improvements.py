"""英文词库展示与收藏规范化回归。旧中文词条不迁移不删。"""
from contextlib import closing
import sqlite3
from unittest import mock
from PyQt5.QtCore import QEvent
from tests.test_vocabulary import StoreCase
from vocabulary_entry import english_word
from vocabulary_ui import VocabularySaveButton, VocabularyWindow
from panel_ui import TranslatePanel


class TestEnglishVocabulary(StoreCase):
    def test_word_edge_punctuation_and_apostrophe(self):
        for text, expected in (("‘expect,’", "expect"), ("time.", "time"),
                               ("don’t", "don't"), ("well-known", "well-known")):
            self.assertEqual(english_word(text), expected)
        for sentence in ("hello world", "two words.", "收获", "123", "a--b"):
            self.assertFalse(english_word(sentence))

    def test_punctuated_word_saved_english(self):
        button = VocabularySaveButton(self.store)
        events = []
        button.feedback.connect(events.append)
        button.set_result("‘expect,’", "vt. 期待", "百度")
        button.click()
        self.assertEqual(self.store.search()[0]["word"], "expect")
        self.assertIn("expect 已加入", events[0])

    def test_chinese_new_collection_not_permitted(self):
        button = VocabularySaveButton(self.store)
        button.set_result("收获", "harvest; gain", "百度")
        self.assertFalse(button.isEnabled())
        with self.assertRaises(ValueError):
            self.store.add("收获", "harvest")

    def legacy(self, word, meaning):
        self.store.search()  # schema
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO vocabulary VALUES (?,?,?,?,?)", (word, word, meaning, "百度", "2026-01-01"))

    def test_chinese_legacy_english_label_chinese_detail_and_key(self):
        self.legacy("收获", "harvest; gain; gather in the crops")
        window = VocabularyWindow(self.store)
        window.refresh()
        item = window.word_list.item(0)
        self.assertEqual(item.text(), "harvest")
        self.assertIn("中文释义:\n收获", window.detail_edit.toPlainText())
        from PyQt5.QtCore import Qt
        self.assertEqual(item.data(Qt.UserRole)["word_key"], "收获")
        self.assertEqual(self.store.search()[0]["word"], "收获")
        window.search_edit.setText("harvest")
        self.assertEqual(window.word_list.count(), 1)
        window.close()

    def test_unresolved_legacy_kept_explicitly(self):
        self.legacy("旧记录", "There is no single translation")
        window = VocabularyWindow(self.store)
        window.refresh()
        self.assertEqual(window.word_list.count(), 0)
        self.assertFalse(window.legacy_box.isHidden())
        window.legacy_box.setChecked(True)
        self.assertEqual(window.word_list.count(), 1)
        self.assertIn("待确认", window.detail_edit.toPlainText())
        self.assertEqual(len(self.store.search()), 1)
        window.close()

    def test_english_legacy_duplicate_label_does_not_delete_other(self):
        self.store.add("harvest", "n. 收获")
        self.legacy("收获", "harvest; gain")
        window = VocabularyWindow(self.store)
        window.refresh()
        self.assertEqual(window.word_list.count(), 2)
        window.close()

    def test_panel_selects_existing_input_on_present(self):
        panel = TranslatePanel(self.store)
        panel.input_edit.setPlainText("old word")
        panel.present()
        from PyQt5.QtTest import QTest
        QTest.qWait(200)
        self.assertEqual(panel.input_edit.textCursor().selectedText(), "old word")
        panel.close()

    def test_panel_focus_does_not_steal_after_hidden(self):
        panel = TranslatePanel(self.store)
        panel._focus_requested = True
        panel.hide()
        panel.event(QEvent(QEvent.WindowDeactivate))
        self.assertFalse(panel._focus_requested)
        self.assertFalse(panel._focus_timer.isActive())
        panel.close()
