from app.services.session_store import SessionStore


def test_cleanup_only_removes_old_closed_sessions() -> None:
    store = SessionStore()
    session = store.create()
    store.set_status(session.session_id, "closed")

    removed = store.cleanup_older_than(max_age_minutes=-1)
    assert removed == 1
    assert store.get(session.session_id) is None
