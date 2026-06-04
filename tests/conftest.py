import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings


@pytest.fixture(autouse=True)
def default_test_runtime(monkeypatch, tmp_path):
    monkeypatch.setenv("UPSTREAM_MODE", "mock")
    monkeypatch.setenv("AUTH_MODE", "disabled")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
