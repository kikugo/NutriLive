from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from uuid import uuid4


@dataclass
class LiveSession:
    session_id: str
    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    status: str = "created"


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, LiveSession] = {}
        self._lock = Lock()

    def create(self) -> LiveSession:
        with self._lock:
            session = LiveSession(session_id=str(uuid4()))
            self._sessions[session.session_id] = session
            return session

    def get(self, session_id: str) -> LiveSession | None:
        return self._sessions.get(session_id)

    def set_status(self, session_id: str, status: str) -> None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.status = status

    def cleanup_older_than(self, max_age_minutes: int) -> int:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=max_age_minutes)
        with self._lock:
            ids_to_delete = [
                session_id
                for session_id, session in self._sessions.items()
                if session.created_at < cutoff and session.status == "closed"
            ]
            for session_id in ids_to_delete:
                del self._sessions[session_id]
            return len(ids_to_delete)

    def stats(self) -> dict[str, int]:
        with self._lock:
            total = len(self._sessions)
            created = sum(1 for session in self._sessions.values() if session.status == "created")
            active = sum(1 for session in self._sessions.values() if session.status == "active")
            closed = sum(1 for session in self._sessions.values() if session.status == "closed")
            return {
                "total": total,
                "created": created,
                "active": active,
                "closed": closed,
            }

    def list_sessions(self, status: str | None = None) -> list[LiveSession]:
        sessions = list(self._sessions.values())
        if not status:
            return sessions
        return [session for session in sessions if session.status == status]


session_store = SessionStore()
