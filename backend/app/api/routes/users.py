"""Simple users (no auth)."""

import sqlite3

from fastapi import APIRouter, HTTPException

from app.core.database import get_conn
from app.core.models import User, UserCreate, UserUpdate
from app.core.session_store import get_session_store

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[User])
def list_users() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@router.post("", response_model=User, status_code=201)
def create_user(payload: UserCreate) -> dict:
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, display_name) VALUES (?, ?)",
                (payload.username, payload.display_name),
            )
            row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="username already exists") from None
    return dict(row)


@router.patch("/{user_id}", response_model=User)
def update_user(user_id: int, payload: UserUpdate) -> dict:
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "UPDATE users SET username = ?, display_name = ? WHERE id = ?",
                (payload.username, payload.display_name, user_id),
            )
            if cur.rowcount == 0:
                raise HTTPException(status_code=404, detail="user not found")
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="username already exists") from None
    return dict(row)


@router.delete("/{user_id}")
def delete_user(user_id: int) -> dict:
    """Remove a user and everything that belongs to them: sessions (TinyDB),
    messages and compactions (SQLite). user_facts cascade with the row."""
    store = get_session_store()
    session_ids = [s["id"] for s in store.list_sessions(user_id)]
    with get_conn() as conn:
        user = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")
        if session_ids:
            ph = ",".join("?" for _ in session_ids)
            conn.execute(f"DELETE FROM compactions WHERE session_id IN ({ph})", session_ids)
            conn.execute(f"DELETE FROM messages WHERE session_id IN ({ph})", session_ids)
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    for sid in session_ids:
        store.delete(sid)
    return {"deleted": True}
