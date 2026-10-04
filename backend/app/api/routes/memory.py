"""Memory & metrics stats for the dashboard's Memory panel.

One read-only endpoint aggregating the durable stores (SQLite transcript /
user facts / compactions, TinyDB sessions / skills, optional ChromaDB) plus
the per-turn context-budget accounting from settings.
"""

from fastapi import APIRouter, HTTPException

from app.agent import tokenizer
from app.agent.memory import SkillStore, VectorRecall
from app.core.config import settings
from app.core.database import (
    get_conn,
    get_user_facts_summary,
    list_compactions,
    list_user_facts,
)
from app.core.models import MemoryStats
from app.core.session_store import get_session_store

router = APIRouter(prefix="/api/memory", tags=["memory"])
_recall = VectorRecall()


@router.get("/stats", response_model=MemoryStats)
def memory_stats(user_id: int, session_id: int | None = None) -> dict:
    store = get_session_store()
    with get_conn() as conn:
        user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")
        messages_total = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE is_deleted = 0"
        ).fetchone()[0]
        session_rows: list[dict] = []
        if session_id is not None:
            if not store.exists(session_id):
                raise HTTPException(status_code=404, detail="session not found")
            session_rows = [
                dict(r)
                for r in conn.execute(
                    "SELECT role, content FROM messages WHERE session_id = ? "
                    "AND is_deleted = 0 ORDER BY id",
                    (session_id,),
                ).fetchall()
            ]

    facts = list_user_facts(user_id)
    facts_summary = get_user_facts_summary(user_id) or ""
    skills = SkillStore().list_skills()
    compactions = list_compactions(session_id) if session_id is not None else []
    latest_summary = compactions[-1]["summary"] if compactions else ""

    # system_prompt counts the base system prompt; the injected user-facts
    # system message is counted under user_facts.
    return {
        "external_store": {
            "vector_recall": _recall.healthy,
            "messages_total": messages_total,
            "messages_session": len(session_rows),
            "sessions_total": len(store.list_sessions(user_id)),
        },
        "context_budget": {
            "total": settings.converse_token_budget,
            "system_prompt": tokenizer.estimate_tokens(settings.base_system_prompt),
            "compaction": tokenizer.estimate_tokens(latest_summary),
            "current_chat": sum(
                tokenizer.estimate_tokens(r["content"]) for r in session_rows
            ),
            "user_facts": tokenizer.estimate_tokens(facts_summary),
            "skills": sum(
                tokenizer.estimate_tokens(s["name"] + " " + (s.get("description") or ""))
                for s in skills
            ),
        },
        "skills": [
            {
                "id": s["doc_id"],
                "name": s["name"],
                "description": s.get("description") or "",
                "created_at": s.get("created_at"),
            }
            for s in skills
        ],
        "user_facts": facts,
        "compactions": compactions,
    }
