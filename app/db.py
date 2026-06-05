import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    last_activity_at TEXT NOT NULL,
    status TEXT NOT NULL
);
"""

# Paths whose schema migration has already run this process.
_migrated: set[str] = set()


def resolve_path(db_path: str | None) -> str:
    return db_path or get_settings().database_path


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns missing from databases created by older schema versions."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)")}
    if "user_id" not in columns:
        conn.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT NOT NULL DEFAULT ''")


@contextmanager
def connection(db_path: str | None = None) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection, ensure schema, commit on success, always close.

    A fresh connection per operation keeps the stores thread-safe under the
    threaded TestClient and uvicorn workers without juggling a shared handle.
    """
    path = resolve_path(db_path)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    if path not in _migrated:
        _migrate(conn)
        _migrated.add(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
