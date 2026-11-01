"""Excel export service — one .xlsx workbook, one sheet per table.

Written by the Settings page (`Export all to Excel`). Honest by design:
  * works in every mode (demo rows are labelled DEMO in the meta sheet)
  * empty tables still get a sheet so the structure documents itself
  * returns bytes — nothing is written to disk without the user's download
"""
from __future__ import annotations

import io
from datetime import datetime

import pandas as pd


def collect_tables() -> tuple[dict[str, pd.DataFrame], str]:
    """Gather every exportable table from the active data source.

    Returns ({sheet_name: dataframe}, mode). Pages never call this directly;
    ui/settings uses it so UI stays free of data plumbing.
    """
    from data import source

    mode = source.mode()
    frames: dict[str, pd.DataFrame] = {}

    def frame(rows: list, columns: list[str]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame(columns=columns)
        df = pd.DataFrame([{k: r.get(k) for k in columns} for r in rows])
        return df

    frames["tasks"] = frame(
        source.load_tasks(active_only=False),
        ["title", "status", "priority_band", "priority_score", "estimated_minutes",
         "due_date", "notes", "created_at", "completed_at"])
    frames["projects"] = frame(
        source.load_projects(),
        ["name", "status", "priority", "deadline", "progress_pct", "github_url", "notes"])
    frames["milestones"] = frame(
        source.load_milestones(),
        ["title", "status", "due_date", "project_id"])
    frames["skills"] = frame(
        source.load_skills(),
        ["name", "category", "current_level", "target_level", "minutes_goal_weekly",
         "last_practiced", "status"])
    frames["goals"] = frame(
        source.load_goals(),
        ["title", "horizon", "target_date", "target_role", "target_compensation",
         "progress_pct", "status"])
    frames["career_milestones"] = frame(
        source.load_career_milestones(),
        ["title", "status", "due_date", "category", "notes"])
    frames["english_logs"] = frame(
        source.load_english_logs(),
        ["practice_type", "minutes", "confidence", "notes", "logged_on"])
    frames["notifications"] = frame(
        source.load_notifications(),
        ["notif_type", "severity", "title", "body", "created_at", "is_read"])

    meta = pd.DataFrame([{
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "data_mode": mode,
        "app": "AI Productivity & Career Tracker v3.0",
        "note": ("Sample data" if mode == "demo" else
                 "Persistent local SQLite" if mode == "local" else
                 "Supabase live rows"),
    }])
    frames = {"_meta": meta, **frames}
    return frames, mode


def export_all_xlsx() -> bytes:
    """Serialise the collected tables into a single in-memory .xlsx."""
    frames, _mode = collect_tables()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in frames.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    return buf.getvalue()
