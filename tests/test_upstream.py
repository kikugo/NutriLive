import pytest

from app.config import get_settings
from app.services.upstream import (
    GeminiUpstreamClient,
    UpstreamClient,
    UpstreamInitError,
    UpstreamNotStartedError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
    create_upstream_client,
)


def test_create_upstream_client_default_mode(monkeypatch) -> None:
    monkeypatch.setenv("UPSTREAM_MODE", "mock")
    get_settings.cache_clear()
    client = create_upstream_client()
    assert isinstance(client, UpstreamClient)
    get_settings.cache_clear()


def test_create_upstream_client_gemini_mode(monkeypatch) -> None:
    monkeypatch.setenv("UPSTREAM_MODE", "gemini")
    get_settings.cache_clear()
    client = create_upstream_client()
    assert isinstance(client, GeminiUpstreamClient)
    get_settings.cache_clear()


def test_create_upstream_client_rejects_unknown_mode(monkeypatch) -> None:
    monkeypatch.setenv("UPSTREAM_MODE", "bogus")
    get_settings.cache_clear()
    with pytest.raises(UpstreamInitError) as info:
        create_upstream_client()
    assert info.value.code == "UPSTREAM_INIT_FAILED"
    get_settings.cache_clear()


async def test_send_text_before_start_raises_not_started() -> None:
    client = UpstreamClient()
    with pytest.raises(UpstreamNotStartedError) as info:
        await client.send_text("hello")
    assert info.value.code == "SESSION_NOT_STARTED"


def test_error_codes_are_distinct() -> None:
    assert UpstreamNotStartedError.code == "SESSION_NOT_STARTED"
    assert UpstreamInitError.code == "UPSTREAM_INIT_FAILED"
    assert UpstreamTimeoutError.code == "UPSTREAM_TIMEOUT"
    assert UpstreamUnavailableError.code == "UPSTREAM_UNAVAILABLE"
