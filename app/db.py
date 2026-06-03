import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS meals (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    calories INTEGER NOT NULL,
    protein INTEGER NOT NULL,
    carbs INTEGER NOT NULL,
    fat INTEGER NOT NULL,
    fiber INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    last_activity_at TEXT NOT NULL,
    status TEXT NOT NULL
);
"""


def resolve_path(db_path: str | None) -> str:
    return db_path or get_settings().database_path


@contextmanager
def connection(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection, ensure schema, commit on success, always close.

    A fresh connection per operation keeps the stores thread-safe under the
    threaded TestClient and uvicorn workers without juggling a shared handle.
    """
    conn = sqlite3.connect(resolve_path(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
