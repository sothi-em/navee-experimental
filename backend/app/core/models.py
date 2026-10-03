"""Pydantic request/response models."""

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str | None = None


class User(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    created_at: str | None = None


class SessionCreate(BaseModel):
    user_id: int
    title: str | None = None


class Session(BaseModel):
    id: int
    user_id: int
    title: str | None = None
    created_at: str | None = None


class MessageIn(BaseModel):
    role: str
    content: str


class Message(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: str | None = None
