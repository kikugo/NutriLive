import asyncio

from fastapi import WebSocket

from app.schemas import PrepareMealLogArgs
from app.services.upstream import UpstreamClient, create_upstream_client


class LiveBridge:
    def __init__(self, upstream_client: UpstreamClient | None = None) -> None:
        self._upstream_client = upstream_client or create_upstream_client()
        self._send_lock = asyncio.Lock()

    async def _send_json(self, websocket: WebSocket, payload: dict) -> None:
        async with self._send_lock:
            await websocket.send_json(payload)

    async def _handle_upstream_event(self, websocket: WebSocket, event: dict) -> None:
        await self._send_json(websocket, event)

    async def handle_start(self, websocket: WebSocket) -> None:
        await self._upstream_client.start(
            lambda event: self._handle_upstream_event(websocket, event)
        )
        await self._send_json(
            websocket,
            {
                "type": "ready",
                "message": "Live session started",
                "protocol_version": "v1",
            },
        )

    async def handle_audio_chunk(self, websocket: WebSocket, payload: dict) -> None:
        audio = payload.get("audio") or {}
        data = audio.get("data")
        mime_type = audio.get("mime_type", "audio/pcm;rate=16000")

        if not data:
            await self._send_json(websocket, {"type": "error", "message": "Missing audio.data"})
            return

        await self._upstream_client.send_audio_chunk(data, mime_type)
        await self._send_json(
            websocket,
            {
                "type": "server_ack",
                "event": "audio_chunk_received",
                "mime_type": mime_type,
                "bytes_base64_len": len(data),
            },
        )

    async def handle_text(self, websocket: WebSocket, payload: dict) -> None:
        text = payload.get("text", "").strip()
        if not text:
            await self._send_json(websocket, {"type": "error", "message": "Missing text"})
            return

        await self._send_json(websocket, {"type": "user_transcript", "text": text, "finished": True})
        upstream_response = await self._upstream_client.send_text(text)
        if upstream_response.text:
            await self._send_json(
                websocket,
                {
                    "type": "model_transcript",
                    "text": upstream_response.text,
                    "finished": True,
                },
            )

        if upstream_response.tool_call:
            meal_args = PrepareMealLogArgs(
                name="Estimated meal",
                calories=450,
                protein=30,
                carbs=42,
                fat=15,
                fiber=8,
                type="lunch",
            )
            await self._send_json(
                websocket,
                {
                    "type": "tool_call",
                    "name": "prepare_meal_log",
                    "args": meal_args.model_dump(),
                },
            )

    async def handle_stop(self, websocket: WebSocket) -> None:
        await self._upstream_client.stop()
        await self._send_json(websocket, {"type": "done", "reason": "client_stop"})
