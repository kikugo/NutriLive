from fastapi import WebSocket

from app.schemas import PrepareMealLogArgs


class LiveBridge:
    """
    Bridge implementation that validates WS contract events and emits
    deterministic responses while full Gemini Live proxying is wired.
    """

    async def handle_start(self, websocket: WebSocket) -> None:
        await websocket.send_json(
            {
                "type": "ready",
                "message": "Live session started",
                "protocol_version": "v1",
            }
        )

    async def handle_audio_chunk(self, websocket: WebSocket, payload: dict) -> None:
        audio = payload.get("audio") or {}
        data = audio.get("data")
        mime_type = audio.get("mime_type", "audio/pcm;rate=16000")

        if not data:
            await websocket.send_json({"type": "error", "message": "Missing audio.data"})
            return

        await websocket.send_json(
            {
                "type": "server_ack",
                "event": "audio_chunk_received",
                "mime_type": mime_type,
                "bytes_base64_len": len(data),
            }
        )

    async def handle_text(self, websocket: WebSocket, payload: dict) -> None:
        text = payload.get("text", "").strip()
        if not text:
            await websocket.send_json({"type": "error", "message": "Missing text"})
            return

        await websocket.send_json({"type": "user_transcript", "text": text, "finished": True})
        await websocket.send_json(
            {
                "type": "model_transcript",
                "text": f"I heard: {text}",
                "finished": True,
            }
        )

        if "log meal" in text.lower():
            meal_args = PrepareMealLogArgs(
                name="Estimated meal",
                calories=450,
                protein=30,
                carbs=42,
                fat=15,
                fiber=8,
                type="lunch",
            )
            await websocket.send_json(
                {
                    "type": "tool_call",
                    "name": "prepare_meal_log",
                    "args": meal_args.model_dump(),
                }
            )

    async def handle_stop(self, websocket: WebSocket) -> None:
        await websocket.send_json({"type": "done", "reason": "client_stop"})


live_bridge = LiveBridge()
