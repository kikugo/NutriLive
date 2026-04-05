from app.config import get_settings
from app.services.upstream import GeminiUpstreamClient, UpstreamClient, create_upstream_client


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
