"""Deterministic task priority scoring — pure Python, no I/O, no AI.

Principle: "Python decides, AI explains."
This scoring is 100% reproducible; the same inputs always produce the same
score, which is why it can be unit-tested.

Formula (kept simple and explainable on the UI):
    impact_pts  = impact * 2.0            impact 1..5  -> 2..10
    effort_pts  = (5 - effort) * 0.6      small tasks get a nudge (0..2.4)
    urgency_pts = overdue 5.5 | ramps down to 0 at ~6 days out | 0
    band_pts    = high 3.0 | medium 1.5 | low 0.0
    score       = round(impact + effort_pts + urgency + band, 1)
"""
from datetime import date, datetime

BAND_POINTS = {"low": 0.0, "medium": 1.5, "high": 3.0}


def compute_priority_score(
    *,
    impact: int,
    effort: int,
    priority_band: str,
    due_date: date | None,
    today: date | None = None,
) -> float:
    """Return the deterministic priority score of a task.

    All params validated; bad values raise ValueError early (fail loudly at
    data-entry boundaries, fail softly in UI).
    """
    if today is None:
        today = date.today()

    if not (1 <= impact <= 5):
        raise ValueError(f"impact must be 1..5, got {impact}")
    if not (1 <= effort <= 5):
        raise ValueError(f"effort must be 1..5, got {effort}")
    if priority_band not in BAND_POINTS:
        raise ValueError(f"priority_band must be one of {sorted(BAND_POINTS)}, got {priority_band!r}")

    impact_pts = impact * 2.0
    effort_pts = (5 - effort) * 0.6

    if due_date is None:
        urgency_pts = 0.0
    else:
        if isinstance(due_date, str):
            due_date = date.fromisoformat(due_date[:10])
        if isinstance(due_date, datetime):
            due_date = due_date.date()
        days_left = (due_date - today).days
        if days_left <= 0:
            urgency_pts = 5.5          # today or overdue: max urgency
        else:
            urgency_pts = max(0.0, 5.0 - 0.8 * days_left)

    score = impact_pts + effort_pts + urgency_pts + BAND_POINTS[priority_band]
    return round(score, 1)
