from dataclasses import dataclass


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


def create_upstream_client() -> UpstreamClient:
    return UpstreamClient()
