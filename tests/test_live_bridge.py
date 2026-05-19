import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app
from app.services.live_bridge import LiveBridge
from app.services.upstream import UpstreamClient


client = TestClient(app)


class UnhealthyUpstream(UpstreamClient):
    def ensure_healthy(self) -> None:
        raise RuntimeError("Upstream receive loop failed")


@pytest.mark.asyncio
async def test_live_bridge_raises_when_upstream_unhealthy() -> None:
    bridge = LiveBridge(upstream_client=UnhealthyUpstream())
    with pytest.raises(RuntimeError, match="Upstream receive loop failed"):
        await bridge.handle_text(None, {"text": "hello"})  # type: ignore[arg-type]


def test_websocket_reports_upstream_failure(monkeypatch) -> None:
    class FailingBridge:
        async def handle_start(self, websocket):
            return

        async def handle_audio_chunk(self, websocket, payload):
            raise RuntimeError("bridge failed")

        async def handle_text(self, websocket, payload):
            raise RuntimeError("bridge failed")

        async def handle_stop(self, websocket):
            return

    monkeypatch.setattr(main_module, "LiveBridge", FailingBridge)
    response = client.post("/v1/live/session")
    session_id = response.json()["session_id"]
    with client.websocket_connect(f"/v1/live/ws/{session_id}") as websocket:
        websocket.receive_json()
        websocket.send_json({"type": "audio_chunk", "audio": {"data": "AAA=", "mime_type": "audio/pcm;rate=16000"}})
        error_event = websocket.receive_json()
        assert error_event["type"] == "error"
        assert error_event["code"] == "UPSTREAM_ERROR"
