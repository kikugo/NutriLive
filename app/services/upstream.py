from dataclasses import dataclass

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
    async def start(self) -> None:
        settings = get_settings()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required when UPSTREAM_MODE=gemini")
        await super().start()

    async def send_text(self, text: str) -> UpstreamResponse:
        if not self._started:
            raise RuntimeError("Upstream session has not started")
        return UpstreamResponse(
            text=f"Gemini mode is enabled. Echo response: {text}",
            tool_call="log meal" in text.lower(),
        )


def create_upstream_client() -> UpstreamClient:
    settings = get_settings()
    mode = settings.upstream_mode.lower()
    if mode == "gemini":
        return GeminiUpstreamClient()
    if mode == "mock":
        return UpstreamClient()
    raise RuntimeError(f"Unsupported UPSTREAM_MODE: {settings.upstream_mode}")
