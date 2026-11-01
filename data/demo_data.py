"""Demo/sample data — clearly labelled, session-interactive, DB-free.

Every page shows a demo-mode banner when data comes from here. Mutations
made in demo mode (completing tasks, adding items) live in st.session_state
copies so interactions feel real and reset on refresh.
"""
import random
from datetime import date, timedelta

import streamlit as st

TODAY = date.today()


def _d(offset: int) -> str:
    return (TODAY + timedelta(days=offset)).isoformat()


def _seed() -> dict:
    return {
        "tasks": [
            {"id": "demo-t1", "user_id": "demo", "title": "Finish SQL joins practice set",
             "notes": "Chapters 4-5", "priority_band": "high", "impact": 5, "effort": 3,
             "priority_score": 14.2, "estimated_minutes": 45, "due_date": _d(0),
             "project_id": "demo-p1", "status": "in_progress"},
            {"id": "demo-t2", "user_id": "demo", "title": "Draft portfolio project README",
             "notes": "", "priority_band": "high", "impact": 4, "effort": 2,
             "priority_score": 12.0, "estimated_minutes": 30, "due_date": _d(0),
             "project_id": "demo-p1", "status": "todo"},
            {"id": "demo-t3", "user_id": "demo", "title": "Revise hypothesis testing notes",
             "notes": "", "priority_band": "medium", "impact": 3, "effort": 2,
             "priority_score": 8.5, "estimated_minutes": 40, "due_date": _d(-1),
             "project_id": None, "status": "todo"},
            {"id": "demo-t4", "user_id": "demo", "title": "Watch Power BI DAX basics",
             "notes": "", "priority_band": "medium", "impact": 3, "effort": 2,
             "priority_score": 7.8, "estimated_minutes": 50, "due_date": _d(2),
             "project_id": None, "status": "todo"},
            {"id": "demo-t5", "user_id": "demo", "title": "Send 2 job applications",
             "notes": "Curated roles only", "priority_band": "high", "impact": 4, "effort": 3,
             "priority_score": 10.4, "estimated_minutes": 35, "due_date": _d(3),
             "project_id": None, "status": "todo"},
            {"id": "demo-t6", "user_id": "demo", "title": "English: record 10-min speak run",
             "notes": "", "priority_band": "low", "impact": 2, "effort": 1,
             "priority_score": 5.0, "estimated_minutes": 10, "due_date": _d(-2),
             "project_id": None, "status": "todo"},
            {"id": "demo-t7", "user_id": "demo", "title": "Complete pandas groupby exercise",
             "notes": "", "priority_band": "medium", "impact": 4, "effort": 3,
             "priority_score": 9.0, "estimated_minutes": 55, "due_date": _d(-3),
             "project_id": "demo-p2", "status": "done", "completed_at": f"{_d(-3)}T08:30"},
            {"id": "demo-t8", "user_id": "demo", "title": "Set up GitHub Actions linter",
             "notes": "", "priority_band": "medium", "impact": 3, "effort": 2,
             "priority_score": 8.0, "estimated_minutes": 25, "due_date": _d(-2),
             "project_id": "demo-p1", "status": "done", "completed_at": f"{_d(-2)}T09:10"},
            {"id": "demo-t9", "user_id": "demo", "title": "Clean performance dashboard mockups",
             "notes": "", "priority_band": "low", "impact": 2, "effort": 3,
             "priority_score": 5.0, "estimated_minutes": 60, "due_date": _d(-4),
             "project_id": "demo-p2", "status": "done", "completed_at": f"{_d(-4)}T19:00"},
            {"id": "demo-t10", "user_id": "demo", "title": "Review ML roadmap week-1 notes",
             "notes": "", "priority_band": "medium", "impact": 3, "effort": 2,
             "priority_score": 8.0, "estimated_minutes": 35, "due_date": _d(-5),
             "project_id": None, "status": "done", "completed_at": f"{_d(-5)}T07:45"},
            {"id": "demo-t11", "user_id": "demo", "title": "Refactor tracker core module",
             "notes": "WBS-style decomposition", "priority_band": "medium",
             "impact": 3, "effort": 3, "priority_score": 7.0, "estimated_minutes": 40,
             "due_date": _d(-6), "project_id": "demo-p2", "status": "done",
             "completed_at": f"{_d(-6)}T20:15"},
        ],
        "projects": [
            {"id": "demo-p1", "user_id": "demo", "name": "Career Portfolio site",
             "description": "Personal portfolio + this tracker shipped publicly.",
             "github_url": "https://github.com/ajaymithran/ai-productivity-career-tracker",
             "start_date": _d(-21), "target_date": _d(10), "status": "in_progress",
             "blockers": "None", "notes": ""},
            {"id": "demo-p2", "user_id": "demo", "name": "Data study dashboard",
             "description": "Study-hours and habit analytics mini app.",
             "github_url": None, "start_date": _d(-35), "target_date": _d(24),
             "status": "in_progress", "blockers": "Waiting for mockup feedback",
             "notes": ""},
            {"id": "demo-p3", "user_id": "demo", "name": "SQL drills notebook",
             "description": "Daily practice log notebook.", "github_url": None,
             "start_date": _d(-50), "target_date": _d(-2), "status": "done",
             "blockers": None, "notes": ""},
        ],
        "milestones": [
            {"id": "demo-m1", "project_id": "demo-p1", "title": "Repo + CI green",
             "position": 1, "due_date": _d(-5), "status": "done", "user_id": "demo"},
            {"id": "demo-m2", "project_id": "demo-p1", "title": "Home page polish",
             "position": 2, "due_date": _d(2), "status": "in_progress", "user_id": "demo"},
            {"id": "demo-m3", "project_id": "demo-p1", "title": "Case study section",
             "position": 3, "due_date": _d(9), "status": "pending", "user_id": "demo"},
            {"id": "demo-m4", "project_id": "demo-p2", "title": "Mockups approved",
             "position": 1, "due_date": _d(1), "status": "blocked",
             "blocker": "Awaiting reviewer feedback", "user_id": "demo"},
            {"id": "demo-m5", "project_id": "demo-p2", "title": "Charts module",
             "position": 2, "due_date": _d(12), "status": "pending", "user_id": "demo"},
            {"id": "demo-m6", "project_id": "demo-p3", "title": "50 problems logged",
             "position": 1, "due_date": _d(-3), "status": "done", "user_id": "demo"},
        ],
        "skills": [
            {"id": "demo-s1", "user_id": "demo", "name": "Python", "category": "Programming",
             "current_level": 4, "target_level": 5, "minutes_goal_weekly": 240,
             "status": "active", "last_practiced": _d(-1), "linked_projects": ["Career Portfolio site"]},
            {"id": "demo-s2", "user_id": "demo", "name": "SQL", "category": "Data Analytics",
             "current_level": 3, "target_level": 5, "minutes_goal_weekly": 180,
             "status": "active", "last_practiced": _d(-1), "linked_projects": ["SQL drills notebook"]},
            {"id": "demo-s3", "user_id": "demo", "name": "Excel", "category": "Data Analytics",
             "current_level": 4, "target_level": 4, "minutes_goal_weekly": 60,
             "status": "active", "last_practiced": _d(-6), "linked_projects": []},
            {"id": "demo-s4", "user_id": "demo", "name": "Power BI", "category": "Data Analytics",
             "current_level": 2, "target_level": 4, "minutes_goal_weekly": 120,
             "status": "active", "last_practiced": _d(-4), "linked_projects": ["Data study dashboard"]},
            {"id": "demo-s5", "user_id": "demo", "name": "Statistics", "category": "Data Science",
             "current_level": 3, "target_level": 4, "minutes_goal_weekly": 90,
             "status": "active", "last_practiced": _d(-2), "linked_projects": []},
            {"id": "demo-s6", "user_id": "demo", "name": "Machine Learning", "category": "AI/ML",
             "current_level": 1, "target_level": 4, "minutes_goal_weekly": 150,
             "status": "active", "last_practiced": _d(-7), "linked_projects": []},
            {"id": "demo-s7", "user_id": "demo", "name": "AI tools", "category": "AI/ML",
             "current_level": 3, "target_level": 5, "minutes_goal_weekly": 60,
             "status": "active", "last_practiced": _d(0), "linked_projects": []},
            {"id": "demo-s8", "user_id": "demo", "name": "English", "category": "Communication",
             "current_level": 3, "target_level": 5, "minutes_goal_weekly": 120,
             "status": "active", "last_practiced": _d(-2), "linked_projects": []},
            {"id": "demo-s9", "user_id": "demo", "name": "Communication", "category": "Communication",
             "current_level": 2, "target_level": 4, "minutes_goal_weekly": 60,
             "status": "active", "last_practiced": _d(-2), "linked_projects": []},
        ],
        "goals": [
            {"id": "demo-g1", "user_id": "demo", "title": "Land a Junior Data Analyst role",
             "horizon": "mid_term", "target_date": _d(75), "status": "active",
             "progress_pct": 35},
            {"id": "demo-g2", "user_id": "demo", "title": "Ship portfolio with 3 public projects",
             "horizon": "short_term", "target_date": _d(12), "status": "active",
             "progress_pct": 45},
            {"id": "demo-g3", "user_id": "demo", "title": "English upper-intermediate confident speaking",
             "horizon": "long_term", "target_date": _d(120), "status": "active",
             "progress_pct": 20},
        ],
        "career_milestones": [
            {"id": "demo-cm1", "title": "Master Excel + Power BI basics", "when": _d(-14),
             "status": "completed"},
            {"id": "demo-cm2", "title": "SQL joins to window functions", "when": _d(0),
             "status": "active"},
            {"id": "demo-cm3", "title": "Portfolio: 3 polished projects", "when": _d(12),
             "status": "active"},
            {"id": "demo-cm4", "title": "Resume v2 ready", "when": _d(18), "status": "pending"},
            {"id": "demo-cm5", "title": "First applications wave", "when": _d(30),
             "status": "pending"},
            {"id": "demo-cm6", "title": "Mock interviews + offers", "when": _d(70),
             "status": "pending"},
        ],
        "english_logs": [
            {"id": "demo-e1", "user_id": "demo", "practice_type": "speaking",
             "minutes": 15, "confidence": 3, "notes": "Rehearsed standup intro",
             "logged_on": _d(-1), "skill_id": "demo-s8"},
            {"id": "demo-e2", "user_id": "demo", "practice_type": "listening",
             "minutes": 25, "confidence": 4, "notes": "Podcast",
             "logged_on": _d(-2), "skill_id": "demo-s8"},
            {"id": "demo-e3", "user_id": "demo", "practice_type": "vocabulary",
             "minutes": 12, "confidence": 3, "notes": "Work-edition deck",
             "logged_on": _d(-4), "skill_id": "demo-s8"},
        ],
        "notifications": [
            {"id": "demo-n1", "notif_type": "deadline", "severity": "urgent",
             "title": "Overdue: Revise hypothesis testing notes", "route": "planner",
             "is_read": False, "created_at": f"{_d(0)}T06:00", "user_id": "demo"},
            {"id": "demo-n2", "notif_type": "deadline", "severity": "warning",
             "title": "Due today: Finish SQL joins practice set", "route": "planner",
             "is_read": False, "created_at": f"{_d(0)}T06:00", "user_id": "demo"},
            {"id": "demo-n3", "notif_type": "weekly_review", "severity": "info",
             "title": "Weekly review ready", "route": "roadmap",
             "is_read": False, "created_at": f"{_d(-1)}T17:00", "user_id": "demo"},
        ],
        "settings": {
            "user_id": "demo", "display_name": "Ajay Mithran",
            "daily_study_minutes": 120, "study_start_time": "06:30",
            "study_end_time": "22:00", "weekly_review_day": 0,
            "theme": "light", "ai_enabled": True, "ai_tone": "mentor",
        },
        "ai_proposals": [
            {"id": "demo-ap1", "scope": "ai", "model": "demo", "status": "pending",
             "created_at": _d(0), "user_id": "demo",
             "prompt_context": {"overdue_tasks": ["Revise hypothesis testing notes"]},
             "proposal": {"text": (
                 "Suggested today plan (demo proposal):\n"
                 "1. 06:30-07:15 - Finish SQL joins practice set (45 min)\n"
                 "2. 07:15-07:40 - Revise hypothesis testing notes (25 min, overdue)\n"
                 "3. 18:30-19:40 - Power BI DAX basics (50 min)\n"
                 "4. 19:40-20:00 - English speaking run (10 min)\n"
                 "Reason: overdue first, then priority-score order; fits 120 min availability.")}},
        ],
    }


def data() -> dict:
    """Interactable copy of the demo dataset kept in session state."""
    if "demo" not in st.session_state:
        st.session_state["demo"] = _seed()
    return st.session_state["demo"]


def demo_study_series(days: int = 14) -> list[dict]:
    """Pseudo-random but deterministic study minutes used by analytics."""
    rng = random.Random(42)
    out = []
    for i in range(days, -1, -1):
        day = (TODAY - timedelta(days=i)).isoformat()
        minutes = rng.choice([0, 25, 45, 60, 75, 90, 120]) if i else 95
        done = rng.choice([0, 1, 1, 2, 3]) if minutes else 0
        out.append({"day": day, "minutes": minutes, "completed": done})
    return out
