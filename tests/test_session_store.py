from app.services.session_store import SessionStore


USER = "user-1"


def test_cleanup_only_removes_old_closed_sessions() -> None:
    store = SessionStore()
    session = store.create(USER)
    store.set_status(session.session_id, "closed")

    removed = store.cleanup_older_than(USER, max_age_minutes=-1)
    assert removed == 1
    assert store.get(session.session_id) is None


def test_cleanup_idle_removes_old_active_sessions() -> None:
    store = SessionStore()
    session = store.create(USER)
    store.set_status(session.session_id, "active")

    # Negative threshold pushes the cutoff into the future so any active
    # session counts as idle, without depending on wall-clock waits.
    removed = store.cleanup_idle_older_than(USER, max_idle_minutes=-1)
    assert removed == 1
    assert store.get(session.session_id) is None


def test_cleanup_idle_keeps_recent_active_sessions() -> None:
    store = SessionStore()
    session = store.create(USER)
    store.set_status(session.session_id, "active")

    removed = store.cleanup_idle_older_than(USER, max_idle_minutes=30)
    assert removed == 0
    assert store.get(session.session_id) is not None


def test_sessions_are_isolated_by_user() -> None:
    store = SessionStore()
    mine = store.create(USER)
    store.create("user-2")

    listed = store.list_sessions(USER)
    assert [s.session_id for s in listed] == [mine.session_id]
    assert store.stats(USER)["total"] == 1
