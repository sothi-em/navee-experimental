"""Sessions and transcript.

Sends persist the user turn, call the LLM, and persist the assistant reply —
the minimal loop. Streaming, tool execution, context shaping, and recall
injection are intentionally deferred to a later pass.
"""

from fastapi import APIRouter, HTTPException

from app.agent.llm import LLMClient
from app.core.database import get_conn
from app.core.models import Message, MessageIn, Session, SessionCreate

router = APIRouter(prefix="/api/chat", tags=["chat"])
_llm = LLMClient()


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
            reply = _llm.complete(payload.content)
            conn.execute(
                "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, "assistant", reply),
            )
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY id", (session_id,)
        ).fetchall()
    return [dict(r) for r in rows]
