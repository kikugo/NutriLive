from datetime import datetime, timedelta, timezone

from app.services.session_store import SessionStore


def test_cleanup_only_removes_old_closed_sessions() -> None:
    store = SessionStore()
    session = store.create()
    store.set_status(session.session_id, "closed")

    removed = store.cleanup_older_than(max_age_minutes=-1)
    assert removed == 1
    assert store.get(session.session_id) is None


def test_cleanup_idle_removes_old_active_sessions() -> None:
    store = SessionStore()
    session = store.create()
    store.set_status(session.session_id, "active")
    stale = store.get(session.session_id)
    assert stale is not None
    stale.last_activity_at = datetime.now(tz=timezone.utc) - timedelta(minutes=120)

    removed = store.cleanup_idle_older_than(max_idle_minutes=30)
    assert removed == 1
    assert store.get(session.session_id) is None
