"""Session store (TinyDB): session record + current transcript window.

The transcript window is the message array sent in full to the agent model —
OpenAI wire format, including assistant tool_calls and role:"tool" results.
The durable per-turn transcript lives in SQLite `messages`; this is the
model-facing working copy (tiered state model, docs/chat-memory-architecture.md §1).
"""

from datetime import UTC, datetime

from tinydb.table import Document

from app.core.config import settings
from app.core.database import get_conn
from app.core.models import TranscriptMessage
from app.core.tinydb import get_db


def _now() -> str:
    return datetime.now(UTC).isoformat()


class SessionStore:
    """Sessions in TinyDB; the TinyDB doc_id is the public session id."""

    def __init__(self) -> None:
        self.table = get_db().table("sessions")

    def create(self, user_id: int, title: str | None = None) -> dict:
        """Insert a new session; return the doc plus its id."""
        doc_id = self.table.insert(
            {
                "user_id": user_id,
                "title": title,
                "transcript": [],
                "created_at": _now(),
                "updated_at": _now(),
            }
        )
        return {"id": doc_id, **self.get(doc_id)}

    def get(self, session_id: int) -> dict | None:
        doc = self.table.get(doc_id=session_id)
        if doc is None:
            return None
        return {k: v for k, v in doc.items() if k != "doc_id"}

    def exists(self, session_id: int) -> bool:
        return self.table.get(doc_id=session_id) is not None

    def get_transcript(self, session_id: int) -> list[dict]:
        doc = self.table.get(doc_id=session_id)
        return list(doc["transcript"]) if doc else []

    def replace_transcript(self, session_id: int, transcript: list[dict]) -> None:
        """Validate + replace the whole window. Raises KeyError if missing.

        The original dicts are stored as-is (validation only) so the window
        stays a byte-stable pass-through to the model — model_dump would add
        None defaults for fields the caller didn't send.
        """
        for m in transcript:
            TranscriptMessage.model_validate(m)
        updated = self.table.update(
            {"transcript": transcript, "updated_at": _now()},
            doc_ids=[session_id],
        )
        if not updated:
            raise KeyError(f"session {session_id} not found")

    def delete(self, session_id: int) -> None:
        self.table.remove(doc_ids=[session_id])


_stores: dict[str, SessionStore] = {}


def get_session_store() -> SessionStore:
    """Per-path accessor (mirrors get_db) so tests with patched paths are isolated."""
    path = settings.tinydb_path
    if path not in _stores:
        _stores[path] = SessionStore()
    return _stores[path]


def migrate_legacy_sessions() -> None:
    """One-time: move sessions from the legacy SQLite table into TinyDB.

    Runs on every startup; a no-op once the SQLite table is gone. Existing
    session ids are preserved via explicit TinyDB doc_id so messages rows and
    stored frontend session ids keep working.
    """
    with get_conn() as conn:
        legacy = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'sessions'"
        ).fetchone()
        if legacy is None:
            return
        rows = conn.execute(
            "SELECT id, user_id, title, created_at FROM sessions ORDER BY id"
        ).fetchall()
    store = get_session_store()
    for row in rows:
        if not store.exists(row["id"]):
            store.table.insert(
                Document(
                    {
                        "user_id": row["user_id"],
                        "title": row["title"],
                        "transcript": [],
                        "created_at": row["created_at"] or _now(),
                        "updated_at": _now(),
                    },
                    row["id"],
                )
            )
    with get_conn() as conn:
        # With foreign_keys ON, DROP TABLE sessions cascades and deletes the
        # legacy messages rows that reference it. The new schema has no FK, so
        # drop with enforcement off and leave the rows as (harmless) orphans.
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DROP TABLE sessions")
