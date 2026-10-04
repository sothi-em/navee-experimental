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
    facts_summary TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    role       TEXT NOT NULL,
    content    TEXT NOT NULL,
    metadata   TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    is_deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT
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

CREATE TABLE IF NOT EXISTS user_facts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fact       TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_user_facts_user ON user_facts(user_id, id);
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


def migrate_messages_schema() -> None:
    """Bring a legacy messages table up to the current schema; no-op when fresh.

    Two legacy shapes, each handled once:
    1. A dangling ``REFERENCES sessions(id)`` FK — sessions moved to TinyDB
       and the SQLite table was dropped, so with foreign_keys ON any DML on
       messages fails with ``no such table: main.sessions``; the table is
       rebuilt without the FK.
    2. Missing soft-delete columns (``is_deleted`` flag, ``deleted_at``
       timestamp) — added in place.
    """
    with get_conn() as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'messages'"
        ).fetchone()
        if row is None:
            return
        if "REFERENCES sessions" in (row[0] or ""):
            conn.executescript(
                """
                CREATE TABLE messages_new (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    role       TEXT NOT NULL,
                    content    TEXT NOT NULL,
                    metadata   TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    is_deleted INTEGER NOT NULL DEFAULT 0,
                    deleted_at TEXT
                );
                INSERT INTO messages_new
                    (id, session_id, role, content, metadata, created_at)
                    SELECT id, session_id, role, content, metadata, created_at FROM messages;
                DROP TABLE messages;
                ALTER TABLE messages_new RENAME TO messages;
                CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
                """
            )
        cols = {r[1] for r in conn.execute("PRAGMA table_info(messages)")}
        if "is_deleted" not in cols:
            conn.execute(
                "ALTER TABLE messages ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0"
            )
        if "deleted_at" not in cols:
            conn.execute("ALTER TABLE messages ADD COLUMN deleted_at TEXT")


def migrate_users_schema() -> None:
    """Bring a legacy users table up to the current schema; no-op when fresh."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
        if row is None:
            return
        cols = {r[1] for r in conn.execute("PRAGMA table_info(users)")}
        if "facts_summary" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN facts_summary TEXT")


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


def add_user_fact(user_id: int, fact: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO user_facts (user_id, fact) VALUES (?, ?)", (user_id, fact)
        )
        return cur.lastrowid


def list_user_facts(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM user_facts WHERE user_id = ? ORDER BY id", (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_user_fact(fact_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM user_facts WHERE id = ?", (fact_id,))


def set_user_facts_summary(user_id: int, summary: str | None) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE users SET facts_summary = ? WHERE id = ?", (summary, user_id))


def get_user_facts_summary(user_id: int) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT facts_summary FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return row["facts_summary"] if row else None


def _placeholders(ids: list[int]) -> str:
    return ",".join("?" for _ in ids)


def list_compactions_for_sessions(session_ids: list[int]) -> list[dict]:
    """Compactions across the given sessions, oldest first."""
    if not session_ids:
        return []
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM compactions WHERE session_id IN ({_placeholders(session_ids)}) "
            "ORDER BY id",
            session_ids,
        ).fetchall()
    return [dict(r) for r in rows]


def delete_compaction(compaction_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM compactions WHERE id = ?", (compaction_id,))


def clear_compactions_for_sessions(session_ids: list[int]) -> int:
    """Hard-delete compactions for the given sessions; returns rows removed."""
    if not session_ids:
        return 0
    with get_conn() as conn:
        cur = conn.execute(
            f"DELETE FROM compactions WHERE session_id IN ({_placeholders(session_ids)})",
            session_ids,
        )
        return cur.rowcount


def list_messages_for_sessions(session_ids: list[int]) -> list[dict]:
    """Live (non-deleted) messages across the given sessions, oldest first."""
    if not session_ids:
        return []
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT * FROM messages WHERE session_id IN ({_placeholders(session_ids)}) "
            "AND is_deleted = 0 ORDER BY id",
            session_ids,
        ).fetchall()
    return [dict(r) for r in rows]


def clear_messages_for_sessions(session_ids: list[int]) -> int:
    """Soft-delete messages for the given sessions (matches session delete);
    returns rows affected."""
    if not session_ids:
        return 0
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE messages SET is_deleted = 1, deleted_at = datetime('now') "
            f"WHERE session_id IN ({_placeholders(session_ids)}) AND is_deleted = 0",
            session_ids,
        )
        return cur.rowcount


def clear_user_facts(user_id: int) -> int:
    """Delete all of a user's facts; returns rows removed."""
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM user_facts WHERE user_id = ?", (user_id,))
        return cur.rowcount
