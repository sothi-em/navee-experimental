"""Store-level tests: TinyDB session/skill stores and SQLite compactions."""

import pytest

from app.agent.memory import SkillStore
from app.core.config import settings
from app.core.database import (
    add_compaction,
    add_user_fact,
    delete_user_fact,
    get_conn,
    get_user_facts_summary,
    init_db,
    list_compactions,
    list_user_facts,
    migrate_messages_schema,
    set_user_facts_summary,
)
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


def test_set_initial_title(stores) -> None:
    store = get_session_store()
    sid = store.create(1)["id"]

    # Short message: whitespace collapsed, used as-is.
    store.set_initial_title(sid, "  how   do I\nship this?  ")
    assert store.get(sid)["title"] == "how do I ship this?"

    # A second message never overwrites the initial title.
    store.set_initial_title(sid, "something else entirely")
    assert store.get(sid)["title"] == "how do I ship this?"

    # Long message: first 30 characters + ellipsis.
    long_sid = store.create(1)["id"]
    long = "x" * 30 + " y" * 10
    store.set_initial_title(long_sid, long)
    assert store.get(long_sid)["title"] == "x" * 30 + "…"

    # Explicitly titled sessions are never touched; missing ones are a no-op.
    titled = store.create(1, "keep me")["id"]
    store.set_initial_title(titled, "nope")
    assert store.get(titled)["title"] == "keep me"
    store.set_initial_title(999, "ghost")


def test_skill_fields(stores) -> None:
    store = SkillStore()
    store.add_skill("summarize", "Summarizes long threads.", "Step 1: collect turns.")
    skill = store.list_skills()[-1]
    assert skill["name"] == "summarize"
    assert skill["description"] == "Summarizes long threads."
    assert skill["content"] == "Step 1: collect turns."
    assert skill["created_at"]


def test_get_skill_by_name(stores) -> None:
    store = SkillStore()
    store.add_skill("test-skill", "desc", "full content here")
    skill = store.get_skill_by_name("test-skill")
    assert skill is not None
    assert skill["content"] == "full content here"
    assert store.get_skill_by_name("nonexistent") is None


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


def test_legacy_messages_fk_migration(stores) -> None:
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
    # Lifespan order: rebuild messages before the sessions table is dropped.
    migrate_messages_schema()
    migrate_legacy_sessions()
    with get_conn() as conn:
        assert conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sessions'"
        ).fetchone() is None
        # Pre-existing rows survive the rebuild...
        assert conn.execute(
            "SELECT content FROM messages WHERE session_id = 1"
        ).fetchone()[0] == "kept"
        # ...and DML works even though the FK target table no longer exists.
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (1, 'assistant', 'hi')"
        )
        conn.execute("DELETE FROM messages WHERE session_id = 1")
    assert get_session_store().get(1) is not None


def test_messages_schema_adds_soft_delete_columns(stores) -> None:
    with get_conn() as conn:
        # Replicate the pre-soft-delete shape: no FK, no soft-delete columns.
        conn.execute("DROP TABLE messages")
        conn.execute(
            "CREATE TABLE messages (id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "session_id INTEGER NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, "
            "metadata TEXT, created_at TEXT DEFAULT (datetime('now')))"
        )
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (1, 'user', 'kept')"
        )
    migrate_messages_schema()
    with get_conn() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(messages)")}
        assert {"is_deleted", "deleted_at"} <= cols
        content, is_deleted, deleted_at = conn.execute(
            "SELECT content, is_deleted, deleted_at FROM messages WHERE session_id = 1"
        ).fetchone()
        assert content == "kept" and is_deleted == 0 and deleted_at is None
    # Idempotent: a second run is a no-op.
    migrate_messages_schema()


def test_user_facts_roundtrip(stores) -> None:
    with get_conn() as conn:
        conn.execute("INSERT INTO users (username) VALUES (?)", ("dave",))
        user_id = conn.execute(
            "SELECT id FROM users WHERE username = 'dave'"
        ).fetchone()[0]
    fid = add_user_fact(user_id, "Prefers dark mode")
    facts = list_user_facts(user_id)
    assert [f["fact"] for f in facts] == ["Prefers dark mode"]
    assert facts[0]["id"] == fid
    set_user_facts_summary(user_id, "Likes dark mode.")
    assert get_user_facts_summary(user_id) == "Likes dark mode."
    delete_user_fact(fid)
    assert list_user_facts(user_id) == []


def test_truncate_to_tokens(stores) -> None:
    from app.agent.tokenizer import count_tokens, truncate_to_tokens

    text = " ".join(f"word{i}" for i in range(200))
    out = truncate_to_tokens(text, 10)
    assert count_tokens(out) <= 10
    assert out != text
    assert truncate_to_tokens("", 10) == ""
    assert truncate_to_tokens(text, 0) == ""
