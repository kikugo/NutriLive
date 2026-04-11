from dataclasses import dataclass
import asyncio

from app.config import get_settings


@dataclass
class UpstreamResponse:
    text: str
    tool_call: bool = False


class UpstreamClient:
    def __init__(self) -> None:
        self._started = False

    async def start(self) -> None:
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

    async def start(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required when UPSTREAM_MODE=gemini")
        try:
            from google import genai
        except Exception as exc:  # pragma: no cover - import error depends on local env
            raise RuntimeError("google-genai is not installed") from exc

        self._client = genai.Client(api_key=settings.gemini_api_key)
        await super().start()

    async def send_text(self, text: str) -> UpstreamResponse:
        if not self._started:
            raise RuntimeError("Upstream session has not started")
        if self._client is None:
            raise RuntimeError("Gemini client is not initialized")

        settings = get_settings()

        def _generate() -> str:
            response = self._client.models.generate_content(
                model=settings.gemini_model,
                contents=text,
            )
            return response.text or ""

        model_text = await asyncio.to_thread(_generate)
        return UpstreamResponse(text=model_text, tool_call="log meal" in text.lower())


def create_upstream_client() -> UpstreamClient:
    settings = get_settings()
    mode = settings.upstream_mode.lower()
    if mode == "gemini":
        return GeminiUpstreamClient()
    if mode == "mock":
        return UpstreamClient()
    raise RuntimeError(f"Unsupported UPSTREAM_MODE: {settings.upstream_mode}")
