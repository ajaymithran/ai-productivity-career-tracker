"""Local SQLite adapter: persistence across connections, idempotent
notifications, decision history. Uses a temp DB — never the real
tracker_local.db."""
import pytest


@pytest.fixture
def store(tmp_path, monkeypatch):
    from src.database import local_store as ls
    monkeypatch.setattr(ls, "DB_PATH", tmp_path / "unit.db")
    ls.init_db()
    return ls


def test_task_persists_across_connections(store):
    store.insert_task({"title": "Write chapter 4", "impact": 4, "effort": 2})
    # every call opens a NEW sqlite connection internally — reading here
    # already proves it survived across connections
    tasks = store.list_tasks(active_only=False)
    assert len(tasks) == 1 and tasks[0]["title"] == "Write chapter 4"
    assert tasks[0]["priority_score"] > 0


def test_completion_sets_timestamp_and_filters_active(store):
    t = store.insert_task({"title": "done-de-me"})
    store.set_status(t["id"], "completed")
    active = store.list_tasks(active_only=True)
    assert all(x["id"] != t["id"] for x in active)
    all_rows = store.list_tasks(active_only=False)
    saved = next(x for x in all_rows if x["id"] == t["id"])
    assert saved["status"] == "completed" and saved["completed_at"]


def test_update_and_delete(store):
    t = store.insert_task({"title": "Scratch"}).copy()
    store.update_task(t["id"], {"title": "Scratch II", "estimated_minutes": 45})
    rows = store.list_tasks(active_only=False)
    assert rows[0]["title"] == "Scratch II" and rows[0]["estimated_minutes"] == 45
    store.delete_task(t["id"])
    assert store.list_tasks(active_only=False) == []


def test_settings_roundtrip(store):
    store.set_setting_json("user_settings", {"daily_study_minutes": 150})
    assert store.get_setting_json("user_settings", {})["daily_study_minutes"] == 150


def test_notifications_are_idempotent_per_day(store):
    ok1 = store.create_notification("deadline", "warning", "Due today: Revise SQL")
    ok2 = store.create_notification("deadline", "warning", "Due today: Revise SQL")
    assert ok1 is True and ok2 is False            # retry adds nothing
    assert len(store.list_notifications()) == 1
    # a genuinely different notice still gets created
    ok3 = store.create_notification("deadline", "info", "Upcoming: Mock test")
    assert ok3 is True
    assert len(store.list_notifications()) == 2


def test_decision_history_roundtrip(store):
    store.record_decision("prop-1", "approve", "looks good")
    store.record_decision("prop-1", "reject", "changed my mind")
    rows = store.list_decisions()
    assert len(rows) == 2 and rows[0]["proposal_id"] == "prop-1"
    with pytest.raises(ValueError):
        store.record_decision("prop-2", "maybe")


def test_english_log_roundtrip(store):
    store.insert_english_log({"practice_type": "speaking", "minutes": 30})
    rows = store.list_english_logs()
    assert rows[0]["practice_type"] == "speaking" and rows[0]["minutes"] == 30
