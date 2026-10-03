"""SQLite persistence for users, the full transcript, and compaction history.

The transcript is the durable, human-visible record. The model's per-turn view
is a separate, lossy projection built elsewhere — this DB is the source of
truth for what actually happened in a session. Sessions themselves live in
TinyDB (app/core/session_store.py).
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT UNIQUE NOT NULL,
    display_name TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    metadata   TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);

CREATE TABLE IF NOT EXISTS compactions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id         INTEGER NOT NULL,
    summary            TEXT NOT NULL,
    up_to_message_id   INTEGER,
    messages_compacted INTEGER NOT NULL DEFAULT 0,
    tokens_before      INTEGER,
    tokens_after       INTEGER,
    created_at         TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_compactions_session ON compactions(session_id, id);
"""


def _ensure_dir(path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """Yield a connection with row access; commit on success, roll back on error."""
    _ensure_dir(settings.database_path)
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def add_compaction(
    session_id: int,
    summary: str,
    up_to_message_id: int | None = None,
    messages_compacted: int = 0,
    tokens_before: int | None = None,
    tokens_after: int | None = None,
) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO compactions "
            "(session_id, summary, up_to_message_id, messages_compacted, tokens_before, tokens_after) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                session_id,
                summary,
                up_to_message_id,
                messages_compacted,
                tokens_before,
                tokens_after,
            ),
        )
        return cur.lastrowid


def list_compactions(session_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM compactions WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]
