import asyncio
import base64
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional

from app.config import get_settings


@dataclass
class UpstreamResponse:
    text: str
    tool_call: bool = False


EventHandler = Callable[[dict], Awaitable[None]]


class UpstreamClient:
    def __init__(self) -> None:
        self._started = False

    async def start(self, _: Optional[EventHandler] = None) -> None:
        self._started = True

    async def send_audio_chunk(self, _: str, __: str) -> None:
        if not self._started:
            raise RuntimeError("Upstream session has not started")

    async def send_text(self, text: str) -> UpstreamResponse:
        if not self._started:
            raise RuntimeError("Upstream session has not started")
        return UpstreamResponse(text=f"I heard: {text}", tool_call="log meal" in text.lower())

    async def stop(self) -> None:
        self._started = False


class GeminiUpstreamClient(UpstreamClient):
    def __init__(self) -> None:
        super().__init__()
        self._client = None
        self._session_cm = None
        self._session = None
        self._receiver_task: asyncio.Task | None = None
        self._event_handler: Optional[EventHandler] = None

    async def start(self, event_handler: Optional[EventHandler] = None) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required when UPSTREAM_MODE=gemini")
        try:
            from google import genai
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("google-genai is not installed") from exc

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._event_handler = event_handler
        config = {
            "response_modalities": ["AUDIO"],
            "input_audio_transcription": {},
            "output_audio_transcription": {},
        }
        self._session_cm = self._client.aio.live.connect(
            model=settings.gemini_live_model,
            config=config,
        )
        self._session = await self._session_cm.__aenter__()
        self._receiver_task = asyncio.create_task(self._receive_loop())
        await super().start(event_handler)

    async def send_text(self, text: str) -> UpstreamResponse:
        if not self._started or self._session is None:
            raise RuntimeError("Upstream session has not started")
        await self._session.send_client_content(turns=text, turn_complete=True)
        return UpstreamResponse(text="", tool_call=False)

    async def send_audio_chunk(self, data: str, mime_type: str) -> None:
        if not self._started or self._session is None:
            raise RuntimeError("Upstream session has not started")
        from google.genai import types

        audio_bytes = base64.b64decode(data)
        await self._session.send_realtime_input(
            audio=types.Blob(data=audio_bytes, mime_type=mime_type)
        )

    async def _receive_loop(self) -> None:
        if self._session is None:
            return
        async for response in self._session.receive():
            if self._event_handler is None:
                continue

            server_content = getattr(response, "server_content", None)
            if not server_content:
                continue

            input_tx = getattr(server_content, "input_transcription", None)
            if input_tx and getattr(input_tx, "text", None):
                await self._event_handler(
                    {
                        "type": "user_transcript",
                        "text": input_tx.text,
                        "finished": bool(getattr(input_tx, "finished", False)),
                    }
                )

            output_tx = getattr(server_content, "output_transcription", None)
            if output_tx and getattr(output_tx, "text", None):
                await self._event_handler(
                    {
                        "type": "model_transcript",
                        "text": output_tx.text,
                        "finished": bool(getattr(output_tx, "finished", False)),
                    }
                )

            model_turn = getattr(server_content, "model_turn", None)
            parts = getattr(model_turn, "parts", []) if model_turn else []
            for part in parts:
                inline_data = getattr(part, "inline_data", None)
                if inline_data and getattr(inline_data, "data", None):
                    audio_b64 = base64.b64encode(inline_data.data).decode("utf-8")
                    await self._event_handler(
                        {
                            "type": "model_audio_chunk",
                            "audio": {
                                "data": audio_b64,
                                "mime_type": "audio/pcm;rate=24000",
                            },
                        }
                    )

    async def stop(self) -> None:
        if self._receiver_task:
            self._receiver_task.cancel()
            self._receiver_task = None
        if self._session_cm:
            await self._session_cm.__aexit__(None, None, None)
            self._session_cm = None
            self._session = None
        self._started = False


def create_upstream_client() -> UpstreamClient:
    settings = get_settings()
    mode = settings.upstream_mode.lower()
    if mode == "gemini":
        return GeminiUpstreamClient()
    if mode == "mock":
        return UpstreamClient()
    raise RuntimeError(f"Unsupported UPSTREAM_MODE: {settings.upstream_mode}")
