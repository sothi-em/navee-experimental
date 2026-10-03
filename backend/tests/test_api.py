import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


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
