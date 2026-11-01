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


def test_import_rows_skips_duplicates(monkeypatch):
    """Re-imports never duplicate data: existing titles (case-insensitive)
    plus rows inserted during this same run are skipped."""
    import db.crud as crud
    from core.importer import import_rows

    inserted = []
    monkeypatch.setattr(crud, "list_rows", lambda client, table: [{"title": "Alpha"}])
    def fake_insert(client, table, payload, *, user_id):
        inserted.append(payload)
        return {"id": "new"}
    monkeypatch.setattr(crud, "insert_row", fake_insert)

    rows = pd.DataFrame([
        {"title": "Alpha", "notes": "dupe of existing"},
        {"title": "Beta"},
        {"title": "beta"},          # case-insensitive dupe of row just inserted
    ])
    imported, errors, skipped = import_rows(object(), "tasks", rows, "u1")
    assert imported == 1 and skipped == 2 and errors == []
    assert [p["title"] for p in inserted] == ["Beta"]


def test_import_rows_reports_insert_errors(monkeypatch):
    import db.crud as crud
    from core.importer import import_rows

    monkeypatch.setattr(crud, "list_rows", lambda client, table: [])
    def bad_insert(client, table, payload, *, user_id):
        raise RuntimeError("permission denied")
    monkeypatch.setattr(crud, "insert_row", bad_insert)

    rows = pd.DataFrame([{"title": "X"}])
    imported, errors, skipped = import_rows(object(), "tasks", rows, "u1")
    assert imported == 0 and skipped == 0 and errors and "permission denied" in errors[0]
