"""Tests for the deterministic scheduler core."""
from datetime import date

from core.scheduler import (deadline_notice_level, days_until,
                            next_week_start, select_for_today)

T = date(2026, 3, 10)  # a Tuesday


def mk(i, est=30, due=None, score=5, status="todo"):
    return {"id": str(i), "title": f"t{i}", "estimated_minutes": est,
            "due_date": due, "priority_score": score, "status": status}


def test_overdue_first_then_by_score():
    tasks = [mk("far", due="2026-03-20", score=9),
             mk("late", due="2026-03-08", score=2),
             mk("today", due="2026-03-10", score=5)]
    order = [t["id"] for t in select_for_today(tasks, 600, today=T)]
    assert order == ["late", "today", "far"]


def test_capacity_never_exceeds_availability():
    tasks = [mk("a", est=120), mk("b", est=90), mk("c", est=90), mk("d", est=200)]
    picked = select_for_today(tasks, 300, today=T)
    total = sum(t["estimated_minutes"] for t in picked)
    assert total <= 300


def test_long_task_not_half_scheduled():
    tasks = [mk("small", est=30), mk("huge", est=999)]
    picked = [t["id"] for t in select_for_today(tasks, 100, today=T)]
    assert "small" in picked and "huge" not in picked


def test_done_tasks_never_selected():
    tasks = [mk("done1", est=60, status="done"), mk("open", est=60)]
    picked = [t["id"] for t in select_for_today(tasks, 600, today=T)]
    assert picked == ["open"]


def test_notice_levels():
    assert deadline_notice_level("2026-03-05", today=T) == "urgent"
    assert deadline_notice_level("2026-03-10", today=T) == "warning"
    assert deadline_notice_level("2026-03-12", today=T) == "info"
    assert deadline_notice_level("2026-03-20", today=T) is None
    assert deadline_notice_level(None, today=T) is None


def test_days_until_and_week_anchor():
    assert days_until("2026-03-12", today=T) == 2
    assert days_until(None, today=T) is None
    assert next_week_start(today=T).weekday() == 0   # Monday
