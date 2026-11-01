"""Deterministic scheduling math — pure Python, testable, no I/O, no AI.

Principle: "Python decides, AI explains." Today's helper: what fits inside
an availability window when overloading is not allowed.
"""
from datetime import date, timedelta


def select_for_today(tasks: list[dict], availability_minutes: int,
                     *, today: date | None = None) -> list[dict]:
    """Return the tasks that fit today's window (greedy by priority_score).

    Overdue tasks sort first by deadline, then everything by score.
    A long task that can't fit whole is skipped (never half-scheduled).
    """
    today = today or date.today()
    tiso = today.isoformat()
    opens = [t for t in tasks if t.get("status") not in ("done", "wont_do")]

    def sort_key(t):
        dd = str(t.get("due_date") or "")[:10]
        overdue = dd and dd < tiso
        return (0 if overdue else 1, dd or "9999-12-31",
                -float(t.get("priority_score", 0) or 0))

    chosen, used = [], 0
    for t in sorted(opens, key=sort_key):
        est = int(t.get("estimated_minutes") or 0)
        if used + est <= availability_minutes:
            chosen.append(t)
            used += est
    return chosen


def days_until(deadline: str | None, *, today: date | None = None) -> int | None:
    """Calendar days until a deadline (negative = overdue). None if absent."""
    if not deadline:
        return None
    today = today or date.today()
    due = deadline if isinstance(deadline, date) else date.fromisoformat(str(deadline)[:10])
    return (due - today).days


def deadline_notice_level(deadline: str | None, *, today: date | None = None) -> str | None:
    """Map deadline distance to a notice severity (None = no notice)."""
    d = days_until(deadline, today=today)
    if d is None:
        return None
    if d < 0:
        return "urgent"
    if d == 0:
        return "warning"
    return "info" if d <= 3 else None


def next_week_start(*, today: date | None = None) -> date:
    """ISO Monday on/after today (weekly review anchor)."""
    today = today or date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7)
