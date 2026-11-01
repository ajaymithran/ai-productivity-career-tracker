"""Automation workflows over a pure in-memory store: idempotency +
weekly-day logic, mirroring what the GH Action and local mode run.

Dates are built relative to the REAL date.today() because
core.scheduler.deadline_notice_level reads the real clock."""
from datetime import date


class MemStore:
    def __init__(self, tasks):
        self._tasks = tasks
        self.notifs = []

    def list_tasks(self, active_only: bool = True) -> list[dict]:
        return list(self._tasks)

    def create_notification(self, notif_type: str, severity: str, title: str,
                            body: str = "", route: str = "") -> bool:
        for n in self.notifs:
            if n["title"] == title and n["notif_type"] == notif_type:
                return False
        self.notifs.append({"notif_type": notif_type, "severity": severity,
                            "title": title, "body": body, "route": route})
        return True


def _tasks_for(today: date) -> list[dict]:
    return [
        {"id": "1", "title": "Overdue essay", "due_date": (today).__class__(today.year, today.month, today.day).fromordinal(today.toordinal() - 3).isoformat(), "status": "todo"},
        {"id": "2", "title": "Due today", "due_date": today.isoformat(), "status": "in_progress"},
        {"id": "3", "title": "Soon", "due_date": (today.__class__(today.year, today.month, today.day).fromordinal(today.toordinal() + 2)).isoformat(), "status": "todo"},
        {"id": "4", "title": "Far out", "due_date": (today.__class__(today.year, today.month, today.day).fromordinal(today.toordinal() + 45)).isoformat(), "status": "todo"},
        {"id": "5", "title": "No date", "due_date": None, "status": "todo"},
    ]


def test_first_run_creates_three_notices():
    from automation.workflows import run_all
    store = MemStore(_tasks_for(date.today()))
    result = run_all(store)
    assert result["deadline_notifications"] == 3     # overdue + today + soon
    assert result["ran_on"] == date.today().isoformat()


def test_rerun_is_idempotent():
    from automation.workflows import run_all
    store = MemStore(_tasks_for(date.today()))
    run_all(store)
    again = run_all(store)
    assert again["deadline_notifications"] == 0      # no duplicates on retry
    assert len(store.notifs) == 3 + (1 if date.today().weekday() == 6 else 0)
    # (+1 weekly nudge when today is the default review day, e.g. a Sunday)


def test_weekly_nudge_only_on_review_day():
    from automation import workflows

    def nudge_for(when, review_day: int = 0) -> int:
        class FakeDate(date):
            @classmethod
            def today(cls):
                return when
        real_date = workflows.date
        workflows.date = FakeDate
        try:
            store = MemStore([])
            return workflows.weekly_review_nudge(store, review_day=review_day)
        finally:
            workflows.date = real_date

    sunday = date(2026, 1, 4)             # a Sunday (weekday 6)
    tuesday = date(2026, 1, 6)
    assert nudge_for(tuesday, review_day=0) == 0     # not the review day
    assert nudge_for(sunday, review_day=0) == 1      # default review day = Sunday
    assert nudge_for(tuesday, review_day=2) == 1     # configured day = Tuesday
