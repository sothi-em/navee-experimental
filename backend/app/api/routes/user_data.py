"""Per-user memory management: list, view, delete, and clear a user's
compactions, facts, and chat history.

Compactions and messages are keyed by session in SQLite, while sessions are
keyed by user in TinyDB — so per-user queries join the two stores (session ids
from the session store, rows from SQLite). Facts are already keyed by user.
"""

from fastapi import APIRouter, HTTPException

from app.core.database import (
    clear_compactions_for_sessions,
    clear_messages_for_sessions,
    clear_user_facts as clear_user_facts_db,
    delete_compaction,
    delete_user_fact as delete_user_fact_db,
    get_conn,
    list_compactions_for_sessions,
    list_messages_for_sessions,
    list_user_facts,
    set_user_facts_summary,
)
from app.core.models import Compaction, Message, UserFact
from app.core.session_store import get_session_store

router = APIRouter(prefix="/api/users", tags=["user-data"])


def _session_ids_for_user(user_id: int) -> list[int]:
    """404 when the user is unknown; otherwise the ids of all their sessions."""
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="user not found")
    return [s["id"] for s in get_session_store().list_sessions(user_id)]


# --- Compactions -----------------------------------------------------------


@router.get("/{user_id}/compactions", response_model=list[Compaction])
def get_user_compactions(user_id: int) -> list[dict]:
    return list_compactions_for_sessions(_session_ids_for_user(user_id))


@router.delete("/{user_id}/compactions")
def clear_user_compactions(user_id: int) -> dict:
    deleted = clear_compactions_for_sessions(_session_ids_for_user(user_id))
    return {"deleted": deleted}


@router.delete("/{user_id}/compactions/{compaction_id}")
def delete_user_compaction(user_id: int, compaction_id: int) -> dict:
    session_ids = set(_session_ids_for_user(user_id))
    with get_conn() as conn:
        row = conn.execute(
            "SELECT session_id FROM compactions WHERE id = ?", (compaction_id,)
        ).fetchone()
    if row is None or row["session_id"] not in session_ids:
        raise HTTPException(status_code=404, detail="compaction not found")
    delete_compaction(compaction_id)
    return {"deleted": True}


# --- Facts -----------------------------------------------------------------


@router.get("/{user_id}/facts", response_model=list[UserFact])
def get_user_facts(user_id: int) -> list[dict]:
    _session_ids_for_user(user_id)  # validates the user exists
    return list_user_facts(user_id)


@router.delete("/{user_id}/facts")
def clear_user_facts(user_id: int) -> dict:
    _session_ids_for_user(user_id)  # validates the user exists
    deleted = clear_user_facts_db(user_id)
    # A summary with no underlying facts would still be injected into the LLM
    # context, so drop it alongside the facts.
    set_user_facts_summary(user_id, None)
    return {"deleted": deleted}


@router.delete("/{user_id}/facts/{fact_id}")
def delete_user_fact(user_id: int, fact_id: int) -> dict:
    _session_ids_for_user(user_id)  # validates the user exists
    owned = any(f["id"] == fact_id for f in list_user_facts(user_id))
    if not owned:
        raise HTTPException(status_code=404, detail="fact not found")
    delete_user_fact_db(fact_id)
    return {"deleted": True}


# --- History (full transcript) ---------------------------------------------


@router.get("/{user_id}/history", response_model=list[Message])
def get_user_history(user_id: int) -> list[dict]:
    return list_messages_for_sessions(_session_ids_for_user(user_id))


@router.delete("/{user_id}/history")
def clear_user_history(user_id: int) -> dict:
    deleted = clear_messages_for_sessions(_session_ids_for_user(user_id))
    return {"deleted": deleted}
