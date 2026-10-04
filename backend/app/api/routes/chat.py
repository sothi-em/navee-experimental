"""Sessions and transcript.

`send_message` is the minimal non-streaming loop: persist the user turn, call
the LLM, persist the reply. `stream_message` runs the full agent loop
(streaming + tool execution) over SSE. Sessions live in TinyDB; context
shaping and recall injection remain deferred to a later pass.
"""

import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.agent.agent_loop import run_agent_stream
from app.agent.llm import llm
from app.agent.memory import SkillStore
from app.agent.tokenizer import truncate_to_tokens
from app.core.config import settings
from app.core.database import get_conn, get_user_facts_summary
from app.core.models import (
    ChatStreamIn,
    Message,
    MessageIn,
    Session,
    SessionCreate,
    SessionRename,
)
from app.core.session_store import get_session_store

router = APIRouter(prefix="/api/chat", tags=["chat"])


def _user_facts_system(session_id: int) -> str | None:
    """Budgeted system message with the user's facts summary; None if none."""
    doc = get_session_store().get(session_id)
    if doc is None:
        return None
    summary = get_user_facts_summary(doc["user_id"])
    if not summary:
        return None
    summary = truncate_to_tokens(summary, settings.user_facts_budget)
    return f"Known facts about the user:\n{summary}"


def _skills_system() -> str | None:
    """Budgeted system message listing all skill names + descriptions; None if none."""
    skills = SkillStore().list_skills()
    if not skills:
        return None
    lines = [f"- {s['name']}: {s.get('description', '')}" for s in skills]
    text = "Available skills (use the get_skill tool to fetch full content):\n" + "\n".join(lines)
    return truncate_to_tokens(text, settings.skill_budget)


@router.post("/sessions", response_model=Session, status_code=201)
def create_session(payload: SessionCreate) -> dict:
    with get_conn() as conn:
        user = conn.execute("SELECT id FROM users WHERE id = ?", (payload.user_id,)).fetchone()
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return get_session_store().create(payload.user_id, payload.title)


@router.get("/sessions", response_model=list[Session])
def list_sessions(user_id: int | None = None) -> list[dict]:
    return get_session_store().list_sessions(user_id)


@router.patch("/sessions/{session_id}", response_model=Session)
def rename_session(session_id: int, payload: SessionRename) -> dict:
    store = get_session_store()
    if not store.exists(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    store.set_title(session_id, payload.title)
    return {"id": session_id, **store.get(session_id)}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int) -> dict:
    store = get_session_store()
    if not store.exists(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    with get_conn() as conn:
        # Soft delete: message rows are retained in the datastore, flagged
        # is_deleted + timestamped; every read below filters them out.
        conn.execute(
            "UPDATE messages SET is_deleted = 1, deleted_at = datetime('now') "
            "WHERE session_id = ?",
            (session_id,),
        )
        conn.execute("DELETE FROM compactions WHERE session_id = ?", (session_id,))
    store.delete(session_id)
    return {"deleted": True}


@router.get("/sessions/{session_id}/messages", response_model=list[Message])
def list_messages(session_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? AND is_deleted = 0 ORDER BY id",
            (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/sessions/{session_id}/messages", response_model=list[Message])
def send_message(session_id: int, payload: MessageIn) -> list[dict]:
    if not get_session_store().exists(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, payload.role, payload.content),
        )
        if payload.role == "user":
            get_session_store().set_initial_title(session_id, payload.content)
            system_parts = [settings.base_system_prompt]
            skills_system = _skills_system()
            if skills_system:
                system_parts.append(skills_system)
            facts_system = _user_facts_system(session_id)
            if facts_system:
                system_parts.append(facts_system)
            system = "\n\n".join(system_parts) if system_parts else None
            reply = llm.complete(payload.content, system=system)
            conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, "assistant", reply),
            )
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? AND is_deleted = 0 ORDER BY id",
            (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/sessions/{session_id}/messages/stream")
async def stream_message(session_id: int, payload: ChatStreamIn):
    if not get_session_store().exists(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, 'user', ?)",
            (session_id, payload.content),
        )
        get_session_store().set_initial_title(session_id, payload.content)
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? AND is_deleted = 0 ORDER BY id",
            (session_id,)
        ).fetchall()
    history = [{"role": r["role"], "content": r["content"]} for r in rows]
    facts_system = _user_facts_system(session_id)
    skills_system = _skills_system()
    if skills_system:
        history.insert(0, {"role": "system", "content": skills_system})
    if facts_system:
        history.insert(0, {"role": "system", "content": facts_system})
    history.insert(0, {"role": "system", "content": settings.base_system_prompt})
    return EventSourceResponse(_stream_turn(session_id, history))


async def _stream_turn(session_id: int, history: list[dict]):
    reply_parts: list[str] = []
    tool_events: list[dict] = []
    async for event in run_agent_stream(history):
        if event["type"] == "delta":
            reply_parts.append(event["content"])
        elif event["type"] == "tool":
            tool_events.append(
                {"name": event["name"], "arguments": event["arguments"], "result": event["result"]}
            )
        yield {"event": event["type"], "data": json.dumps(event)}
    reply = "".join(reply_parts)
    message_id = None
    if reply or tool_events:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO messages (session_id, role, content, metadata) "
                "VALUES (?, 'assistant', ?, ?)",
                (
                    session_id,
                    reply,
                    json.dumps({"tool_events": tool_events}) if tool_events else None,
                ),
            )
            message_id = cur.lastrowid
    yield {"event": "done", "data": json.dumps({"type": "done", "message_id": message_id})}
