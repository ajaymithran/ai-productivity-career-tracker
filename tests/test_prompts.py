"""Regression: build_context must tolerate heterogeneous rows (task vs skill)."""
from datetime import date

from ai.prompts import build_context

TASK = {"title": "Write report", "status": "todo", "due_date": "2026-01-05",
        "estimated_minutes": 45, "priority_score": 9.0}
SKILL = {"name": "SQL", "status": "active", "current_level": 3,
         "target_level": 5, "minutes_goal_weekly": 180}
GOAL = {"title": "Analyst role", "status": "active", "target_date": "2026-06-01",
        "progress_pct": 30}


TASK_NO_DUE = {"title": "Read paper", "status": "todo", "due_date": None,
               "estimated_minutes": 45, "priority_score": 9.0}


def test_build_context_handles_skills_without_title():
    ctx = build_context(tasks=[TASK_NO_DUE, SKILL], skills=[SKILL], goals=[GOAL],
                        availability_minutes=120, today=date(2026, 1, 1))
    names = [t["title"] for t in ctx["top_priority_no_due"]]
    assert "SQL" in names and "Read paper" in names


def test_skill_gaps_shape_for_coach():
    ctx = build_context(tasks=[TASK], skills=[SKILL], goals=[GOAL],
                        availability_minutes=90, today=date(2026, 1, 1))
    gap = ctx["skill_gaps"][0]
    assert gap["name"] == "SQL" and gap["level"] == 3 and gap["target"] == 5
    assert ctx["availability_minutes"] == 90
