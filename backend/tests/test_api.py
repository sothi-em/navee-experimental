import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.database import get_conn, set_user_facts_summary
from server import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Isolate storage to a temp dir for the duration of the test.
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
    monkeypatch.setattr(settings, "tinydb_path", str(tmp_path / "test.json"))
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_user_and_session_lifecycle(client: TestClient) -> None:
    # Create a user.
    r = client.post("/api/users", json={"username": "alice", "display_name": "Alice"})
    assert r.status_code == 201
    user_id = r.json()["id"]

    # Duplicate username is rejected.
    r = client.post("/api/users", json={"username": "alice"})
    assert r.status_code == 409

    # Start a session for that user.
    r = client.post("/api/chat/sessions", json={"user_id": user_id, "title": "first"})
    assert r.status_code == 201
    session_id = r.json()["id"]

    # Session for an unknown user is rejected.
    r = client.post("/api/chat/sessions", json={"user_id": 99999})
    assert r.status_code == 404

    # Empty transcript.
    r = client.get(f"/api/chat/sessions/{session_id}/messages")
    assert r.status_code == 200
    assert r.json() == []


def test_session_list_rename_delete(client: TestClient) -> None:
    r = client.post("/api/users", json={"username": "carol"})
    user_id = r.json()["id"]

    # Two sessions list newest-first.
    r = client.post("/api/chat/sessions", json={"user_id": user_id, "title": "one"})
    first = r.json()["id"]
    r = client.post("/api/chat/sessions", json={"user_id": user_id, "title": "two"})
    second = r.json()["id"]

    r = client.get("/api/chat/sessions", params={"user_id": user_id})
    assert r.status_code == 200
    assert [s["id"] for s in r.json()] == [second, first]
    assert r.json()[0]["title"] == "two"

    # Other users' sessions are excluded by the filter.
    r = client.post("/api/users", json={"username": "dave"})
    other_user = r.json()["id"]
    client.post("/api/chat/sessions", json={"user_id": other_user})
    r = client.get("/api/chat/sessions", params={"user_id": user_id})
    assert [s["id"] for s in r.json()] == [second, first]

    # Rename.
    r = client.patch(f"/api/chat/sessions/{first}", json={"title": "renamed"})
    assert r.status_code == 200
    assert r.json()["title"] == "renamed"
    assert client.patch("/api/chat/sessions/99999", json={"title": "x"}).status_code == 404

    # Delete removes the session; messages are soft-deleted (retained in the
    # datastore, marked deleted_at) and hidden from every read.
    r = client.post(
        f"/api/chat/sessions/{second}/messages", json={"role": "user", "content": "hi"}
    )
    assert r.status_code == 200
    r = client.delete(f"/api/chat/sessions/{second}")
    assert r.status_code == 200
    assert r.json() == {"deleted": True}
    r = client.get(f"/api/chat/sessions/{second}/messages")
    assert r.json() == []
    with get_conn() as conn:
        row = conn.execute(
            "SELECT content, is_deleted, deleted_at FROM messages WHERE session_id = ?",
            (second,),
        ).fetchone()
    assert row is not None and row["content"] == "hi"
    assert row["is_deleted"] == 1 and row["deleted_at"]
    assert client.delete(f"/api/chat/sessions/{second}").status_code == 404


def test_stream_message_with_tool_round(client: TestClient, monkeypatch) -> None:
    r = client.post("/api/users", json={"username": "bob"})
    user_id = r.json()["id"]
    r = client.post("/api/chat/sessions", json={"user_id": user_id})
    session_id = r.json()["id"]

    from types import SimpleNamespace

    def _chunk(content=None, tool_calls=None, finish=None):
        return SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=content, tool_calls=tool_calls),
                                     finish_reason=finish)]
        )

    calls = {"n": 0, "tools_seen": None}

    async def fake_stream(self, messages, tools=None):
        calls["n"] += 1
        if calls["n"] == 1:
            calls["tools_seen"] = tools
            yield _chunk(tool_calls=[SimpleNamespace(
                index=0, id="call_1",
                function=SimpleNamespace(name="echo", arguments='{"text": "hi"}'))],
                finish="tool_calls")
        else:
            assert any(m["role"] == "tool" for m in messages)
            yield _chunk(content="Hello from the agent", finish="stop")

    monkeypatch.setattr("app.agent.llm.LLMClient.stream_chat", fake_stream)

    with client.stream("POST", f"/api/chat/sessions/{session_id}/messages/stream",
                       json={"content": "say hi"}) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text()).replace("\r\n", "\n")
    frames = [f for f in body.split("\n\n") if f.strip()]
    events = [f.split("\n")[0] for f in frames]
    assert (
        "event: tool_start" in events
        and "event: tool" in events
        and "event: delta" in events
        and "event: done" in events
    )
    start_frame = next(f for f in frames if f.startswith("event: tool_start\n"))
    assert '"id": "call_1"' in start_frame and '"result"' not in start_frame
    assert events.index("event: tool_start") < events.index("event: tool")
    tool_frame = next(f for f in frames if f.startswith("event: tool\n"))
    assert '"name": "echo"' in tool_frame and '"result": "hi"' in tool_frame
    done_data = next(l.removeprefix("data: ") for f in frames
                     if f.startswith("event: done") for l in f.split("\n") if l.startswith("data:"))
    message_id = json.loads(done_data)["message_id"]
    assert message_id is not None
    assert [t["function"]["name"] for t in calls["tools_seen"]] == ["echo", "get_current_time", "get_skill"]

    r = client.get(f"/api/chat/sessions/{session_id}/messages")
    msgs = r.json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[1]["content"] == "Hello from the agent"

    # tool_events are persisted on the assistant message's metadata (the Message
    # response model omits metadata, so read the row directly).
    from app.core.database import get_conn

    with get_conn() as conn:
        row = conn.execute("SELECT metadata FROM messages WHERE id = ?", (message_id,)).fetchone()
    stored = json.loads(row["metadata"])["tool_events"]
    assert stored[0]["name"] == "echo" and stored[0]["result"] == "hi"


def test_stream_injects_user_facts_summary(client: TestClient, monkeypatch) -> None:
    r = client.post("/api/users", json={"username": "erin"})
    user_id = r.json()["id"]
    r = client.post("/api/chat/sessions", json={"user_id": user_id})
    session_id = r.json()["id"]
    set_user_facts_summary(user_id, "Erin is a backend engineer.")

    from types import SimpleNamespace

    seen = {}

    def _chunk(content=None, finish=None):
        return SimpleNamespace(choices=[SimpleNamespace(
            delta=SimpleNamespace(content=content, tool_calls=None),
            finish_reason=finish)])

    async def fake_stream(self, messages, tools=None):
        seen["messages"] = list(messages)
        yield _chunk(content="ok", finish="stop")

    monkeypatch.setattr("app.agent.llm.LLMClient.stream_chat", fake_stream)
    with client.stream("POST", f"/api/chat/sessions/{session_id}/messages/stream",
                       json={"content": "hi"}) as resp:
        assert resp.status_code == 200
        "".join(resp.iter_text())
    assert seen["messages"][0]["role"] == "system"
    assert seen["messages"][0]["content"] == settings.base_system_prompt
    assert "Erin is a backend engineer." in seen["messages"][1]["content"]
    # The transcript still contains only the real turns.
    r = client.get(f"/api/chat/sessions/{session_id}/messages")
    assert [m["role"] for m in r.json()] == ["user", "assistant"]


def test_stream_injects_skills_system(client: TestClient, monkeypatch) -> None:
    from app.agent.memory import SkillStore

    r = client.post("/api/users", json={"username": "frank"})
    user_id = r.json()["id"]
    r = client.post("/api/chat/sessions", json={"user_id": user_id})
    session_id = r.json()["id"]
    SkillStore().add_skill("my_skill", "does things", "the complete skill body")

    from types import SimpleNamespace

    seen = {}

    def _chunk(content=None, finish=None):
        return SimpleNamespace(choices=[SimpleNamespace(
            delta=SimpleNamespace(content=content, tool_calls=None),
            finish_reason=finish)])

    async def fake_stream(self, messages, tools=None):
        seen["messages"] = list(messages)
        yield _chunk(content="ok", finish="stop")

    monkeypatch.setattr("app.agent.llm.LLMClient.stream_chat", fake_stream)
    with client.stream("POST", f"/api/chat/sessions/{session_id}/messages/stream",
                       json={"content": "hi"}) as resp:
        assert resp.status_code == 200
        "".join(resp.iter_text())
    assert seen["messages"][0]["content"] == settings.base_system_prompt
    assert "my_skill" in seen["messages"][1]["content"]
    assert "does things" in seen["messages"][1]["content"]
    # Skill content is only fetched via the get_skill tool, never in the prompt.
    assert "the complete skill body" not in seen["messages"][1]["content"]


def test_send_message_injects_skills_system(client: TestClient, monkeypatch) -> None:
    from app.agent.memory import SkillStore

    r = client.post("/api/users", json={"username": "grace"})
    user_id = r.json()["id"]
    r = client.post("/api/chat/sessions", json={"user_id": user_id})
    session_id = r.json()["id"]
    SkillStore().add_skill("plain_skill", "plain desc", "plain content")

    seen = {}

    def fake_complete(self, content, system=None):
        seen["system"] = system
        return "ok"

    monkeypatch.setattr("app.agent.llm.LLMClient.complete", fake_complete)
    r = client.post(f"/api/chat/sessions/{session_id}/messages",
                    json={"role": "user", "content": "hi"})
    assert r.status_code == 200
    assert seen["system"] is not None
    assert "plain_skill" in seen["system"]
    assert "plain desc" in seen["system"]


def test_stream_get_skill_tool(client: TestClient, monkeypatch) -> None:
    from app.agent.memory import SkillStore

    r = client.post("/api/users", json={"username": "heidi"})
    user_id = r.json()["id"]
    r = client.post("/api/chat/sessions", json={"user_id": user_id})
    session_id = r.json()["id"]
    SkillStore().add_skill("tool_skill", "tool desc", "tool content body")

    from types import SimpleNamespace

    def _chunk(content=None, tool_calls=None, finish=None):
        return SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content=content, tool_calls=tool_calls),
                                     finish_reason=finish)]
        )

    calls = {"n": 0}

    async def fake_stream(self, messages, tools=None):
        calls["n"] += 1
        if calls["n"] == 1:
            yield _chunk(tool_calls=[SimpleNamespace(
                index=0, id="call_skill",
                function=SimpleNamespace(name="get_skill", arguments='{"name": "tool_skill"}'))],
                finish="tool_calls")
        else:
            assert any(m["role"] == "tool" for m in messages)
            yield _chunk(content="done", finish="stop")

    monkeypatch.setattr("app.agent.llm.LLMClient.stream_chat", fake_stream)
    with client.stream("POST", f"/api/chat/sessions/{session_id}/messages/stream",
                       json={"content": "fetch the skill"}) as resp:
        assert resp.status_code == 200
        body = "".join(resp.iter_text()).replace("\r\n", "\n")
    frames = [f for f in body.split("\n\n") if f.strip()]
    tool_frame = next(f for f in frames if f.startswith("event: tool\n"))
    assert '"name": "get_skill"' in tool_frame
    assert "tool content body" in tool_frame


def test_stream_base_prompt_only(client: TestClient, monkeypatch) -> None:
    r = client.post("/api/users", json={"username": "ivan"})
    user_id = r.json()["id"]
    r = client.post("/api/chat/sessions", json={"user_id": user_id})
    session_id = r.json()["id"]

    from types import SimpleNamespace

    seen = {}

    def _chunk(content=None, finish=None):
        return SimpleNamespace(choices=[SimpleNamespace(
            delta=SimpleNamespace(content=content, tool_calls=None),
            finish_reason=finish)])

    async def fake_stream(self, messages, tools=None):
        seen["messages"] = list(messages)
        yield _chunk(content="ok", finish="stop")

    monkeypatch.setattr("app.agent.llm.LLMClient.stream_chat", fake_stream)
    with client.stream("POST", f"/api/chat/sessions/{session_id}/messages/stream",
                       json={"content": "hi"}) as resp:
        assert resp.status_code == 200
        "".join(resp.iter_text())
    assert seen["messages"][0]["content"] == settings.base_system_prompt
    assert seen["messages"][1]["role"] == "user"


def test_memory_stats(client: TestClient) -> None:
    from app.agent.memory import SkillStore
    from app.core.database import add_compaction, add_user_fact

    user_id = client.post("/api/users", json={"username": "dave"}).json()["id"]
    session_id = client.post(
        "/api/chat/sessions", json={"user_id": user_id}
    ).json()["id"]

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, 'user', ?)",
            (session_id, "hello there"),
        )
    add_user_fact(user_id, "likes tea")
    SkillStore().add_skill("greeting", "say hi", "skill body")
    add_compaction(
        session_id, "summary text", messages_compacted=4,
        tokens_before=100, tokens_after=10,
    )

    r = client.get("/api/memory/stats", params={"user_id": user_id, "session_id": session_id})
    assert r.status_code == 200
    body = r.json()
    ext = body["external_store"]
    assert ext["messages_total"] == 1 and ext["messages_session"] == 1
    assert ext["sessions_total"] == 1
    assert isinstance(ext["vector_recall"], bool)
    b = body["context_budget"]
    assert b["total"] == settings.converse_token_budget
    assert b["current_chat"] > 0 and b["compaction"] > 0 and b["skills"] > 0
    assert b["user_facts"] == 0 and b["system_prompt"] > 0
    assert [s["name"] for s in body["skills"]] == ["greeting"]
    assert "content" not in body["skills"][0]
    assert [f["fact"] for f in body["user_facts"]] == ["likes tea"]
    assert body["compactions"][0]["tokens_before"] == 100


def test_memory_stats_unknown_user_and_session(client: TestClient) -> None:
    assert client.get("/api/memory/stats", params={"user_id": 99999}).status_code == 404
    user_id = client.post("/api/users", json={"username": "frank"}).json()["id"]
    assert (
        client.get(
            "/api/memory/stats", params={"user_id": user_id, "session_id": 424242}
        ).status_code
        == 404
    )


def test_memory_stats_without_session(client: TestClient) -> None:
    user_id = client.post("/api/users", json={"username": "gina"}).json()["id"]
    r = client.get("/api/memory/stats", params={"user_id": user_id})
    assert r.status_code == 200
    body = r.json()
    assert body["external_store"]["messages_session"] == 0
    assert body["context_budget"]["current_chat"] == 0
    assert body["compactions"] == []


def test_memory_stats_tokenizer_fallback(client: TestClient, monkeypatch) -> None:
    from app.agent import tokenizer as tok

    def boom(text: str) -> int:
        raise RuntimeError("no tokenizer")

    monkeypatch.setattr(tok, "count_tokens", boom)
    user_id = client.post("/api/users", json={"username": "hank"}).json()["id"]
    r = client.get("/api/memory/stats", params={"user_id": user_id})
    assert r.status_code == 200
