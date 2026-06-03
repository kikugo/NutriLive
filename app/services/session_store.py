import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.db import connection

_ACTIVE_STATUSES = ("created", "active")


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


@dataclass
class LiveSession:
    session_id: str
    created_at: datetime = field(default_factory=_now)
    last_activity_at: datetime = field(default_factory=_now)
    status: str = "created"


def _row_to_session(row: sqlite3.Row) -> LiveSession:
    return LiveSession(
        session_id=row["session_id"],
        created_at=datetime.fromisoformat(row["created_at"]),
        last_activity_at=datetime.fromisoformat(row["last_activity_at"]),
        status=row["status"],
    )


class SessionStore:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path

    def create(self) -> LiveSession:
        session = LiveSession(session_id=str(uuid4()))
        with connection(self._db_path) as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, created_at, last_activity_at, status)"
                " VALUES (?, ?, ?, ?)",
                (
                    session.session_id,
                    session.created_at.isoformat(),
                    session.last_activity_at.isoformat(),
                    session.status,
                ),
            )
        return session

    def get(self, session_id: str) -> LiveSession | None:
        with connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        return _row_to_session(row) if row else None

    def set_status(self, session_id: str, status: str) -> None:
        with connection(self._db_path) as conn:
            conn.execute(
                "UPDATE sessions SET status = ?, last_activity_at = ? WHERE session_id = ?",
                (status, _now().isoformat(), session_id),
            )

    def touch(self, session_id: str) -> None:
        with connection(self._db_path) as conn:
            conn.execute(
                "UPDATE sessions SET last_activity_at = ? WHERE session_id = ?",
                (_now().isoformat(), session_id),
            )

    def cleanup_older_than(self, max_age_minutes: int) -> int:
        cutoff = (_now() - timedelta(minutes=max_age_minutes)).isoformat()
        with connection(self._db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE created_at < ? AND status = 'closed'",
                (cutoff,),
            )
            return cursor.rowcount

    def cleanup_idle_older_than(self, max_idle_minutes: int) -> int:
        cutoff = (_now() - timedelta(minutes=max_idle_minutes)).isoformat()
        with connection(self._db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM sessions WHERE last_activity_at < ? AND status IN (?, ?)",
                (cutoff, *_ACTIVE_STATUSES),
            )
            return cursor.rowcount

    def stats(self) -> dict[str, int]:
        with connection(self._db_path) as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM sessions GROUP BY status"
            ).fetchall()
        counts = {row["status"]: row["count"] for row in rows}
        return {
            "total": sum(counts.values()),
            "created": counts.get("created", 0),
            "active": counts.get("active", 0),
            "closed": counts.get("closed", 0),
        }

    def list_sessions(self, status: str | None = None) -> list[LiveSession]:
        with connection(self._db_path) as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM sessions WHERE status = ? ORDER BY rowid", (status,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM sessions ORDER BY rowid").fetchall()
        return [_row_to_session(row) for row in rows]


session_store = SessionStore()
