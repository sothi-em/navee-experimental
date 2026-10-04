"""Durable, owner-scoped knowledge stores (external to the live transcript).

Two complementary stores, matching the tiered model in the architecture doc:

- SkillStore: global skills in TinyDB. User-scoped facts live in SQLite
  (app/core/database.py).
- VectorRecall: flat-file ChromaDB index for semantic recall. Optional — if
  ChromaDB is unavailable it degrades to a no-op so core persistence never
  breaks.
"""

from datetime import UTC, datetime
from pathlib import Path

from app.core.config import settings
from app.core.tinydb import get_db


class SkillStore:
    """Persistent store for global skills (TinyDB).

    User-scoped facts live in SQLite (app/core/database.py, user_facts table).
    """

    def __init__(self) -> None:
        self.db = get_db()
        self.skills = self.db.table("skills")

    def add_skill(self, name: str, description: str, content: str) -> int:
        return self.skills.insert(
            {
                "name": name,
                "description": description,
                "content": content,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )

    def list_skills(self) -> list[dict]:
        return [dict(doc, doc_id=doc.doc_id) for doc in self.skills]


class VectorRecall:
    """Flat-file ChromaDB index for semantic recall. Optional and degradable."""

    def __init__(self) -> None:
        self._client = None
        try:
            import chromadb

            Path(settings.chroma_path).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=settings.chroma_path)
        except Exception:  # noqa: BLE001 — missing chroma must not break startup
            self._client = None

    @property
    def healthy(self) -> bool:
        return self._client is not None

    def add(self, collection: str, text: str, metadata: dict | None = None) -> None:
        if not self.healthy:
            return
        col = self._client.get_or_create_collection(collection)
        col.add(documents=[text], metadatas=[metadata or {}])

    def query(self, collection: str, text: str, k: int = 5) -> dict:
        if not self.healthy:
            return {}
        col = self._client.get_or_create_collection(collection)
        if col.count() == 0:
            return {}
        return col.query(query_texts=[text], n_results=min(k, col.count()))
