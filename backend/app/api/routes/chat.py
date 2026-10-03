"""Sessions and transcript.

`send_message` is the minimal non-streaming loop: persist the user turn, call
the LLM, persist the reply. `stream_message` runs the full agent loop
(streaming + tool execution) over SSE. Context shaping and recall injection
are intentionally deferred to a later pass.
"""

import json

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from app.agent.agent_loop import run_agent_stream
from app.agent.llm import llm
from app.core.database import get_conn
from app.core.models import ChatStreamIn, Message, MessageIn, Session, SessionCreate

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/sessions", response_model=Session, status_code=201)
def create_session(payload: SessionCreate) -> dict:
    with get_conn() as conn:
        user = conn.execute("SELECT id FROM users WHERE id = ?", (payload.user_id,)).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")
        cur = conn.execute(
            "INSERT INTO sessions (user_id, title) VALUES (?, ?)",
            (payload.user_id, payload.title),
        )
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@router.get("/sessions/{session_id}/messages", response_model=list[Message])
def list_messages(session_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/sessions/{session_id}/messages", response_model=list[Message])
def send_message(session_id: int, payload: MessageIn) -> list[dict]:
    with get_conn() as conn:
        session = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, payload.role, payload.content),
        )
        if payload.role == "user":
            reply = llm.complete(payload.content)
            conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, "assistant", reply),
            )
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/sessions/{session_id}/messages/stream")
async def stream_message(session_id: int, payload: ChatStreamIn):
    with get_conn() as conn:
        session = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, 'user', ?)",
            (session_id, payload.content),
        )
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
    history = [{"role": r["role"], "content": r["content"]} for r in rows]
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
