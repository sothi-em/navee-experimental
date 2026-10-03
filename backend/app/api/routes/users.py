"""Simple users (no auth)."""

import sqlite3

from fastapi import APIRouter, HTTPException

from app.core.database import get_conn
from app.core.models import User, UserCreate

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
