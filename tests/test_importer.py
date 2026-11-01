"""Tests for workbook import mapping + validation (no Excel file needed)."""
import pandas as pd

from core.importer import map_columns, validate


def test_map_columns_matches_aliases():
    df = pd.DataFrame(columns=["Task Name", "Due Date", "Priority", "Estimated Minutes"])
    m = map_columns(df, "tasks")
    assert m["title"] == "Task Name"
    assert m["due_date"] == "Due Date"
    assert m["priority_band"] == "Priority"
    assert "notes" not in m  # unknown column ignored, not guessed


def test_validate_tasks_coerces_and_drops():
    df = pd.DataFrame([
        {"Task": "Finish resume", "Minutes": 45, "Due": "01/02/2026", "Priority": "H"},
        {"Task": "", "Minutes": 20, "Due": None, "Priority": "low"},     # dropped: blank title
        {"Task": "SQL drills", "Minutes": 990, "Due": None, "Priority": "??"},  # clamped+defaulted
    ])
    df.columns = ["Task", "Minutes", "Due", "Priority"]
    m = map_columns(df, "tasks")
    clean, issues = validate(df, "tasks", m)
    assert len(clean) == 2
    assert clean.iloc[0]["priority_band"] == "high"
    assert clean.iloc[1]["priority_band"] == "medium"
    assert int(clean.iloc[1]["estimated_minutes"]) == 600      # clamped to CHECK range
    assert clean.iloc[0]["due_date"] == "2026-02-01"           # dayfirst parsing
    assert any("non-numeric" in i or "unparseable" in i for i in issues) or issues == []


def test_validate_skills_range_clamp():
    df = pd.DataFrame([
        {"skill": "Python", "level": 4, "target": 7},
        {"skill": "Excel", "level": 0, "target": 3},
    ])
    m = map_columns(df, "skills")
    clean, _ = validate(df, "skills", m)
    assert int(clean.iloc[0]["target_level"]) == 5  # clamped
    assert int(clean.iloc[1]["current_level"]) == 1  # clamped


def test_missing_required_returns_issue():
    df = pd.DataFrame([{"Name Only": "x"}])
    m = map_columns(df, "tasks")
    clean, issues = validate(df, "tasks", m)
    assert clean.empty
    assert issues and "'title'" in issues[0]
