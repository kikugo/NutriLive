from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
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
