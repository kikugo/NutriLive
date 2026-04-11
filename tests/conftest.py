import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import get_settings


@pytest.fixture(autouse=True)
def default_test_runtime(monkeypatch):
    monkeypatch.setenv("UPSTREAM_MODE", "mock")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
