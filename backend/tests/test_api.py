import json

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from server import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Isolate storage to a temp dir for the duration of the test.
    monkeypatch.setattr(settings, "database_path", str(tmp_path / "test.db"))
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
    assert "event: tool" in events and "event: delta" in events and "event: done" in events
    tool_frame = next(f for f in frames if f.startswith("event: tool"))
    assert '"name": "echo"' in tool_frame and '"result": "hi"' in tool_frame
    done_data = next(l.removeprefix("data: ") for f in frames
                     if f.startswith("event: done") for l in f.split("\n") if l.startswith("data:"))
    message_id = json.loads(done_data)["message_id"]
    assert message_id is not None
    assert [t["function"]["name"] for t in calls["tools_seen"]] == ["echo", "get_current_time"]

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
