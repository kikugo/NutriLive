from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_session_then_open_ws() -> None:
    response = client.post("/v1/live/session")
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    with client.websocket_connect(f"/v1/live/ws/{session_id}") as websocket:
        ready_event = websocket.receive_json()
        assert ready_event["type"] == "ready"

        websocket.send_json({"type": "start"})
        started_event = websocket.receive_json()
        assert started_event["type"] == "ready"

        websocket.send_json({"type": "text", "text": "log meal chicken salad"})
        user_event = websocket.receive_json()
        model_event = websocket.receive_json()
        tool_event = websocket.receive_json()

        assert user_event["type"] == "user_transcript"
        assert model_event["type"] == "model_transcript"
        assert tool_event["type"] == "tool_call"
        assert tool_event["name"] == "prepare_meal_log"

        websocket.send_json({"type": "stop"})
        done_event = websocket.receive_json()
        assert done_event["type"] == "done"


def test_ws_rejects_unknown_session() -> None:
    with client.websocket_connect("/v1/live/ws/unknown") as websocket:
        error_event = websocket.receive_json()
        assert error_event["type"] == "error"


def test_ws_rejects_invalid_audio_chunk_payload() -> None:
    response = client.post("/v1/live/session")
    session_id = response.json()["session_id"]

    with client.websocket_connect(f"/v1/live/ws/{session_id}") as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "audio_chunk", "audio": {"mime_type": "audio/pcm;rate=16000"}})
        error_event = websocket.receive_json()
        assert error_event["type"] == "error"
        assert error_event["message"] == "Invalid audio_chunk payload"


def test_ws_rejects_invalid_text_payload() -> None:
    response = client.post("/v1/live/session")
    session_id = response.json()["session_id"]

    with client.websocket_connect(f"/v1/live/ws/{session_id}") as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "text"})
        error_event = websocket.receive_json()
        assert error_event["type"] == "error"
        assert error_event["message"] == "Invalid text payload"


def test_ws_requires_start_before_streaming() -> None:
    response = client.post("/v1/live/session")
    session_id = response.json()["session_id"]

    with client.websocket_connect(f"/v1/live/ws/{session_id}") as websocket:
        websocket.receive_json()
        websocket.send_json(
            {
                "type": "audio_chunk",
                "audio": {"data": "AAA=", "mime_type": "audio/pcm;rate=16000"},
            }
        )
        error_event = websocket.receive_json()
        assert error_event["type"] == "error"
