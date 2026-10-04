"""Pydantic models (request/response + storage)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str | None = None


class UserUpdate(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    display_name: str | None = None


class User(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    facts_summary: str | None = None
    created_at: str | None = None


class UserFact(BaseModel):
    id: int
    user_id: int
    fact: str
    created_at: str | None = None


class SessionCreate(BaseModel):
    user_id: int
    title: str | None = None


class Session(BaseModel):
    id: int
    user_id: int
    title: str | None = None
    created_at: str | None = None


class SessionRename(BaseModel):
    title: str


class MessageIn(BaseModel):
    role: str
    content: str


class ChatStreamIn(BaseModel):
    content: str = Field(min_length=1)


class Message(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    metadata: str | None = None
    created_at: str | None = None


class ToolCallFunction(BaseModel):
    name: str
    arguments: str = ""  # JSON-encoded string, OpenAI wire format


class ToolCall(BaseModel):
    id: str
    type: Literal["function"] = "function"
    function: ToolCallFunction


class TranscriptMessage(BaseModel):
    """One entry of the session transcript window (OpenAI wire format).

    extra="allow": the window is a pass-through to the model — never drop
    fields we don't model yet.
    """

    model_config = ConfigDict(extra="allow")

    role: str
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class SessionDoc(BaseModel):
    """TinyDB session document; the TinyDB doc_id is the session id."""

    user_id: int
    title: str | None = None
    transcript: list[TranscriptMessage] = Field(default_factory=list)
    created_at: str
    updated_at: str


class Skill(BaseModel):
    id: int
    name: str
    description: str = ""  # default: pre-change docs lack the field
    content: str
    created_at: str | None = None


class SkillUpdate(BaseModel):
    name: str = Field(min_length=1)
    description: str = ""
    content: str = ""


class Compaction(BaseModel):
    id: int
    session_id: int
    summary: str
    up_to_message_id: int | None = None
    messages_compacted: int = 0
    tokens_before: int | None = None
    tokens_after: int | None = None
    created_at: str | None = None


class ExternalStoreStats(BaseModel):
    vector_recall: bool
    messages_total: int
    messages_session: int
    sessions_total: int


class ContextBudgetStats(BaseModel):
    total: int
    system_prompt: int
    compaction: int
    current_chat: int
    user_facts: int
    skills: int


class SkillRef(BaseModel):
    """Skill without `content` — the card shows name + description only."""

    id: int
    name: str
    description: str = ""
    created_at: str | None = None


class MemoryStats(BaseModel):
    external_store: ExternalStoreStats
    context_budget: ContextBudgetStats
    skills: list[SkillRef]
    user_facts: list[UserFact]
    compactions: list[Compaction]
