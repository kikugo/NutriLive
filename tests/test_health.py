from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")
    data = response.json()
    assert data["status"] == "ok"


def test_get_live_session_returns_found_after_create() -> None:
    created = client.post("/v1/live/session")
    session_id = created.json()["session_id"]

    response = client.get(f"/v1/live/session/{session_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["session_id"] == session_id


def test_live_stats_returns_counts() -> None:
    response = client.get("/v1/live/stats")
    assert response.status_code == 200
    body = response.json()
    assert "total" in body
    assert "created" in body
    assert "active" in body
    assert "closed" in body


def test_cleanup_endpoint_returns_removed_count() -> None:
    created = client.post("/v1/live/session")
    session_id = created.json()["session_id"]

    with client.websocket_connect(f"/v1/live/ws/{session_id}") as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "start"})
        websocket.receive_json()
        websocket.send_json({"type": "stop"})
        websocket.receive_json()

    cleanup = client.post("/v1/live/cleanup?max_age_minutes=-1")
    assert cleanup.status_code == 200
    body = cleanup.json()
    assert "removed" in body
    assert body["max_age_minutes"] == -1


def test_live_sessions_endpoint_returns_created_sessions() -> None:
    client.post("/v1/live/session")
    response = client.get("/v1/live/sessions")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    assert isinstance(body["sessions"], list)


def test_live_sessions_endpoint_supports_status_filter() -> None:
    response = client.get("/v1/live/sessions?status=created")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["sessions"], list)
