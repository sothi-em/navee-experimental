"""Store-level tests: TinyDB session/skill stores and SQLite compactions."""

import pytest

from app.agent.memory import FactStore
from app.core.config import settings
from app.core.database import add_compaction, get_conn, init_db, list_compactions
from app.core.session_store import get_session_store, migrate_legacy_sessions


@pytest.fixture
def stores(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    monkeypatch.setattr(settings, "tinydb_path", str(tmp_path / "test.json"))
    init_db()
    yield


def test_session_transcript_roundtrip(stores) -> None:
    store = get_session_store()
    doc = store.create(1, "t")
    assert isinstance(doc["id"], int)
    assert store.get_transcript(doc["id"]) == []

    window = [
        {"role": "user", "content": "hi"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "echo", "arguments": '{"text": "hi"}'},
                }
            ],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "hi"},
        {"role": "assistant", "content": "done"},
    ]
    store.replace_transcript(doc["id"], window)
    assert store.get_transcript(doc["id"]) == window


def test_session_store_missing(stores) -> None:
    store = get_session_store()
    assert store.get(999) is None
    assert store.get_transcript(999) == []
    with pytest.raises(KeyError):
        store.replace_transcript(999, [])


def test_skill_fields(stores) -> None:
    store = FactStore()
    store.add_skill("summarize", "Summarizes long threads.", "Step 1: collect turns.")
    skill = store.list_skills()[-1]
    assert skill["name"] == "summarize"
    assert skill["description"] == "Summarizes long threads."
    assert skill["content"] == "Step 1: collect turns."
    assert skill["created_at"]


def test_compactions_order_and_fields(stores) -> None:
    sid = get_session_store().create(1)["id"]
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, 'user', 'a')", (sid,)
        )
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, 'user', 'b')", (sid,)
        )
    first = add_compaction(
        sid,
        "summary one",
        up_to_message_id=2,
        messages_compacted=2,
        tokens_before=100,
        tokens_after=10,
    )
    second = add_compaction(sid, "summary two")
    rows = list_compactions(sid)
    assert [r["id"] for r in rows] == [first, second]
    assert rows[0]["summary"] == "summary one"
    assert rows[0]["up_to_message_id"] == 2
    assert rows[0]["messages_compacted"] == 2
    assert rows[0]["tokens_before"] == 100
    assert rows[0]["tokens_after"] == 10
    assert rows[1]["summary"] == "summary two"
    assert rows[1]["up_to_message_id"] is None
    assert rows[1]["messages_compacted"] == 0
    assert rows[1]["tokens_before"] is None
    assert rows[1]["tokens_after"] is None


def test_legacy_session_migration(stores) -> None:
    with get_conn() as conn:
        # Replicate the legacy DB shape: messages carries an FK to sessions.
        conn.execute("DROP TABLE messages")
        conn.execute(
            "CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE, "
            "role TEXT NOT NULL, content TEXT NOT NULL, metadata TEXT, "
            "created_at TEXT DEFAULT (datetime('now')))"
        )
        conn.execute(
            "CREATE TABLE sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER NOT NULL, title TEXT, created_at TEXT DEFAULT (datetime('now')))"
        )
        conn.execute("INSERT INTO sessions (user_id, title) VALUES (1, 'old')")
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (1, 'user', 'kept')"
        )
    migrate_legacy_sessions()
    doc = get_session_store().get(1)
    assert doc is not None
    assert doc["title"] == "old"
    assert doc["transcript"] == []
    with get_conn() as conn:
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sessions'"
        ).fetchone() is None
        # Dropping the legacy sessions table must not cascade-delete messages.
        assert conn.execute(
            "SELECT content FROM messages WHERE session_id = 1"
        ).fetchone()[0] == "kept"
