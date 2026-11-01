"""Automation workflows — callable from scripts, GH Actions, or tests.

Idempotency contract: daily/weekly runs never duplicate notifications
(same type+title+day is skipped). In live mode the dedupe lives in
db/queries via notifications table; in local mode in local_store.
"""
from __future__ import annotations

from datetime import date


def deadline_notifications(store) -> int:
    """Create notices for overdue / today / 3-day tasks. Returns created count."""
    from core.scheduler import deadline_notice_level
    created = 0
    for t in store.list_tasks(active_only=True):
        level = deadline_notice_level(t.get("due_date"))
        if not level:
            continue
        titles = {"urgent": "Overdue: ", "warning": "Due today: ", "info": "Upcoming: "}
        ok = store.create_notification(
            "deadline", level, f"{titles[level]}{t['title']}",
            body=f"due {t.get('due_date')}", route="planner")
        created += 1 if ok else 0
    return created


def weekly_review_nudge(store, review_day: int = 0) -> int:
    """Nudge on the configured review day (schema: 0=Sunday..6=Saturday,
    which maps to Python weekday (review_day - 1) % 7: Monday=0...Sunday=6)."""
    today = date.today()
    if today.weekday() != (review_day - 1) % 7:
        return 0
    ok = store.create_notification(
        "weekly_review", "info", "Weekly review ready",
        body=f"Covering the week of {today.isoformat()}", route="roadmap")
    return 1 if ok else 0


def run_all(store, review_day: int = 0) -> dict:
    """One automation pass: daily + weekly, idempotent. Safe to re-run."""
    return {
        "deadline_notifications": deadline_notifications(store),
        "weekly_nudge": weekly_review_nudge(store, review_day=review_day),
        "ran_on": date.today().isoformat(),
    }
