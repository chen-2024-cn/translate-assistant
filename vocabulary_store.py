"""本地词库: SQLite 事务持久化,源码和打包版共用同一用户数据目录。"""
from contextlib import contextmanager, closing
from datetime import datetime
from pathlib import Path
import sqlite3

from PyQt5.QtCore import QObject, pyqtSignal

import settings
from vocabulary_entry import english_word


class VocabularyStore(QObject):
    changed = pyqtSignal()

    def __init__(self, path=None):
        super().__init__()
        self.path = Path(path) if path is not None else Path(settings.APP_DIR) / "vocabulary.db"

    @contextmanager
    def _connection(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(str(self.path), timeout=3)) as db:
                db.row_factory = sqlite3.Row
                with db:
                    version = db.execute("PRAGMA user_version").fetchone()[0]
                    if version not in (0, 1):
                        raise RuntimeError("词库版本不兼容,请保留数据并联系维护人员")
                    db.execute("""CREATE TABLE IF NOT EXISTS vocabulary (
                        word_key TEXT PRIMARY KEY,
                        word TEXT NOT NULL,
                        meaning TEXT NOT NULL,
                        engine TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )""")
                    # 校验已有表结构,不覆盖或清空不兼容数据。
                    db.execute("SELECT word_key, word, meaning, engine, created_at FROM vocabulary LIMIT 0")
                    if version == 0:
                        db.execute("PRAGMA user_version = 1")
                    yield db
        except (sqlite3.Error, OSError) as e:
            raise RuntimeError(f"词库读写失败: {e}") from e

    def add(self, word: str, meaning: str, engine: str = "") -> bool:
        word, meaning = english_word(word), meaning.strip()
        if not word or not meaning:
            raise ValueError("词库仅收藏翻译成功的英文单词和中文释义")
        with self._connection() as db:
            cursor = db.execute(
                "INSERT INTO vocabulary (word_key, word, meaning, engine, created_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(word_key) DO NOTHING",
                (word.casefold(), word, meaning, engine, datetime.now().isoformat(timespec="seconds")),
            )
            added = cursor.rowcount == 1
        if added:
            self.changed.emit()
        return added

    def search(self, query: str = "") -> list:
        query = query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{query}%"
        with self._connection() as db:
            rows = db.execute(
                "SELECT * FROM vocabulary WHERE word LIKE ? ESCAPE '\\' "
                "OR meaning LIKE ? ESCAPE '\\' ORDER BY created_at DESC, word_key",
                (pattern, pattern),
            ).fetchall()
        return [dict(row) for row in rows]

    def remove(self, word_key: str) -> bool:
        with self._connection() as db:
            removed = db.execute("DELETE FROM vocabulary WHERE word_key = ?", (word_key,)).rowcount == 1
        if removed:
            self.changed.emit()
        return removed
