"""隔离词库数据与Qt按钮回归,不操作用户词库或真实快捷键。"""
import sqlite3
from contextlib import closing
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PyQt5.QtWidgets import QApplication, QMessageBox

from vocabulary_store import VocabularyStore
from vocabulary_ui import VocabularyWindow, VocabularySaveButton
from panel_ui import TranslatePanel
from popup_ui import TranslatePopup

_APP = QApplication.instance() or QApplication([])


class StoreCase(unittest.TestCase):
    def setUp(self):
        root = Path("artifacts") / "test-temp"
        root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=root)
        self.path = Path(self.temp.name) / "words.db"
        self.store = VocabularyStore(self.path)

    def tearDown(self):
        self.temp.cleanup()


class TestVocabularyStore(StoreCase):
    def test_persists_complete_meaning(self):
        meaning = "n. 时间; 次\nvt. 安排时间"
        self.assertTrue(self.store.add("time", meaning, "百度翻译"))
        entries = VocabularyStore(self.path).search()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["meaning"], meaning)
        self.assertEqual(entries[0]["engine"], "百度翻译")
        self.assertTrue(entries[0]["created_at"])

    def test_duplicate_not_overwritten(self):
        self.store.add("time", "n. 时间", "Google")
        self.assertFalse(self.store.add(" TIME ", "其他释义", "百度"))
        self.assertEqual(len(self.store.search()), 1)
        self.assertEqual(self.store.search()[0]["meaning"], "n. 时间")

    def test_search_word_and_meaning(self):
        self.store.add("time", "n. 时间")
        self.store.add("word", "n. 单词")
        self.assertEqual(self.store.search("TIME")[0]["word"], "time")
        self.assertEqual(self.store.search("时间")[0]["word"], "time")
        self.assertFalse(self.store.search("%"))
        self.assertFalse(self.store.search("' OR 1=1 --"))

    def test_delete_only_selected(self):
        self.store.add("time", "时间")
        self.store.add("word", "单词")
        self.assertTrue(self.store.remove("time"))
        self.assertFalse(self.store.remove("time"))
        self.assertEqual(self.store.search()[0]["word"], "word")

    def test_sentence_and_empty_meaning_rejected(self):
        for word, meaning in (("hello world", "你好世界"), ("time", "  ")):
            with self.assertRaises(ValueError):
                self.store.add(word, meaning)
        self.assertFalse(self.store.search())

    def test_write_failure_does_not_report_success(self):
        self.path.mkdir()
        with self.assertRaises(RuntimeError):
            self.store.add("time", "时间")

    def test_incompatible_database_kept(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE keep_me (value TEXT)")
            db.execute("INSERT INTO keep_me VALUES ('original data')")
            db.execute("PRAGMA user_version = 99")
        with self.assertRaises(RuntimeError):
            self.store.add("time", "时间")
        with closing(sqlite3.connect(self.path)) as db, db:
            self.assertEqual(db.execute("SELECT value FROM keep_me").fetchone()[0], "original data")


class TestVocabularyWidgets(StoreCase):
    def test_button_saved_and_duplicate(self):
        button = VocabularySaveButton(self.store)
        button.set_result("time", "n. 时间", "百度")
        button.click()
        self.assertIn("已加入", button.text())
        button.click()
        self.assertEqual(button.text(), "已在词库")
        self.assertEqual(len(self.store.search()), 1)

    def test_sentence_not_collectable(self):
        button = VocabularySaveButton(self.store)
        button.set_result("hello world", "你好世界", "百度")
        self.assertFalse(button.isEnabled())
        self.assertTrue(button.isHidden())
        button.click()
        self.assertFalse(self.store.search())

    def test_failure_shows_retry(self):
        button = VocabularySaveButton(self.store)
        button.set_result("time", "时间", "百度")
        with mock.patch.object(self.store, "add", side_effect=RuntimeError("磁盘不可写")):
            button.click()
        self.assertIn("保存失败", button.text())
        self.assertIn("磁盘不可写", button.toolTip())
        self.assertFalse(self.store.search())

    def test_panel_late_result_after_edit_not_saved(self):
        panel = TranslatePanel(self.store)
        panel.input_edit.setPlainText("time")
        revision = panel._revision
        panel.input_edit.setPlainText("word")
        panel._on_done("time", "n. 时间", "百度", revision)
        self.assertFalse(panel.result_edit.toPlainText())
        self.assertFalse(panel.save_word_btn.isEnabled())
        panel.close()

    def test_panel_clear_invalidates_even_empty_input(self):
        panel = TranslatePanel(self.store)
        panel.input_edit.setPlainText("time")
        revision = panel._revision
        panel._clear()
        panel._on_done("time", "时间", "百度", revision)
        self.assertFalse(panel.save_word_btn.isEnabled())
        panel.close()

    def test_panel_matching_result_saved(self):
        panel = TranslatePanel(self.store)
        panel.input_edit.setPlainText("time")
        panel._on_done("time", "n. 时间\nvt. 安排时间", "百度", panel._revision)
        panel.save_word_btn.click()
        self.assertEqual(self.store.search()[0]["word"], "time")
        panel.input_edit.setPlainText("word")
        self.assertFalse(panel.save_word_btn.isEnabled())
        panel.close()

    def test_popup_error_and_loading_clear_save(self):
        popup = TranslatePopup(vocabulary=self.store)
        popup.show_result("time", "n. 时间", "百度", 100, 100)
        self.assertTrue(popup.save_word_btn.isEnabled())
        popup.show_loading("word", 100, 100)
        self.assertFalse(popup.save_word_btn.isEnabled())
        popup.show_error("word", "连接失败", 100, 100)
        self.assertFalse(popup.save_word_btn.isEnabled())
        popup.close()

    def test_window_search_and_delete_confirmation(self):
        self.store.add("time", "n. 时间")
        window = VocabularyWindow(self.store)
        window.refresh()
        self.assertEqual(window.word_list.count(), 1)
        self.assertIn("n. 时间", window.detail_edit.toPlainText())
        with mock.patch("vocabulary_ui.QMessageBox.question", return_value=QMessageBox.No):
            window.delete_btn.click()
        self.assertEqual(len(self.store.search()), 1)
        with mock.patch("vocabulary_ui.QMessageBox.question", return_value=QMessageBox.Yes):
            window.delete_btn.click()
        self.assertFalse(self.store.search())
        self.assertFalse(window.delete_btn.isEnabled())
        window.close()


if __name__ == "__main__":
    unittest.main()
