"""Data source abstraction — pages never know where data came from.

mode():
  * "demo" when Supabase is not configured/public  -> clearly labelled
  * "live" otherwise                                -> real DB (existing logic)

Loaders return the same shape in both modes so pages are identical.
In live mode failures degrade to demo with an honest banner.
"""
from __future__ import annotations

import streamlit as st

import data.demo_data as demo
from data.demo_data import data as demo_data


def mode() -> str:
    from config.settings import settings
    if not (settings.supabase_configured() and settings.SUPABASE_USER_EMAIL
            and settings.SUPABASE_USER_PASSWORD):
        return "demo"
    return st.session_state.get("data_mode", "live")


def banner() -> None:
    if mode() == "demo":
        st.info("🧪 **Demo mode — sample data.** Add Supabase credentials to `.env` "
                "(and sign in) to switch to your real database.",
                icon="🧪")


def _db():
    from db.client import get_supabase
    return get_supabase()


def _fallback_db(exc=None) -> dict:
    st.warning(f"Database unavailable right now ({str(exc)[:110] if exc else 'unknown'}) "
               "— showing demo data so the app keeps working.")
    return demo_data()


def load_user() -> dict:
    """Profile row (name, timezone) demo/live."""
    d = demo_data()
    if mode() == "live":
        try:
            client, err = _db()
            if err:
                return d["settings"]
            from db import crud
            rows = crud.list_rows(client, "user_settings")
            prof = d["settings"] | {k: rows[0].get(k) for k in
                                    ("daily_study_minutes", "study_start_time",
                                     "study_end_time", "weekly_review_day",
                                     "ai_enabled", "ai_tone")} if rows else d["settings"]
            return prof
        except Exception as exc:
            _fallback_db(exc)
            return d["settings"]
    return d["settings"]


def load_tasks(active_only: bool = True) -> list[dict]:
    d = demo_data()
    if mode() == "live":
        try:
            client, err = _db()
            if err:
                return d["tasks"]
            from db import crud
            tasks = crud.list_rows(client, "tasks")
        except Exception as exc:
            _fallback_db(exc)
            return d["tasks"]
    else:
        tasks = d["tasks"]
    tasks = [dict(t) for t in tasks]
    for t in tasks:
        t.setdefault("estimated_minutes", 30)
        t.setdefault("priority_score", 0)
        t.setdefault("priority_band", "medium")
    if active_only:
        tasks = [t for t in tasks if t.get("status") not in ("done", "wont_do")]
    return tasks


def load_projects() -> list[dict]:
    d = demo_data()
    return d["projects"]


def load_milestones() -> list[dict]:
    d = demo_data()
    return d["milestones"]


def load_skills() -> list[dict]:
    d = demo_data()
    return d["skills"]


def load_goals() -> list[dict]:
    d = demo_data()
    return d["goals"]


def load_career_milestones() -> list[dict]:
    d = demo_data()
    return d["career_milestones"]


def load_english_logs() -> list[dict]:
    d = demo_data()
    return d["english_logs"]


def load_notifications() -> list[dict]:
    d = demo_data()
    items = d["notifications"]
    if mode() == "live":
        try:
            client, err = _db()
            if err:
                return items
            from db import crud
            return crud.list_rows(client, "notifications", filters={"is_read": False},
                                  order_by="created_at", desc=True)
        except Exception as exc:
            _fallback_db(exc)
            return items
    return items


def load_settings() -> dict:
    d = demo_data()
    return d["settings"]


def load_proposals() -> list[dict]:
    d = demo_data()
    return d["ai_proposals"]


# ---- mutations (session-local in demo mode, DB in live mode) -------------

def complete_task(task: dict) -> None:
    """Demo-mode mutation: mark done in the session-local dataset."""
    import datetime
    d = demo_data()
    for item in d["tasks"]:
        if item["id"] == task["id"]:
            item["status"] = "done"
            item["completed_at"] = (
                f"{datetime.date.today().isoformat()}T{datetime.datetime.now().strftime('%H:%M')}"
            )
            break


def reopen_task(task: dict) -> None:
    d = demo_data()
    for item in d["tasks"]:
        if item["id"] == task["id"]:
            item["status"] = "todo"
            item.pop("completed_at", None)
            break


def update_task(task: dict, changes: dict) -> None:
    d = demo_data()
    for item in d["tasks"]:
        if item["id"] == task["id"]:
            item.update({k: v for k, v in changes.items() if v is not None})
            break


def add_task(fields: dict) -> None:
    d = demo_data()
    from core.priority import compute_priority_score
    d["tasks"].insert(0, {
        "id": f"demo-t{len(d['tasks']) + 1}", "user_id": "demo",
        "notes": "", "priority_score": compute_priority_score(
            impact=int(fields.get("impact", 3)), effort=int(fields.get("effort", 3)),
            priority_band=fields.get("priority_band", "medium"),
            due_date=None if not fields.get("due_date") else fields["due_date"]),
        **fields,
    })


def delete_task(task: dict) -> None:
    d = demo_data()
    d["tasks"] = [t for t in d["tasks"] if t["id"] != task["id"]]


def data_mutator_task(task: dict) -> dict:
    """Deprecated shim kept for imports during refactor — no-op."""
    return task


def toggle_task_done(task: dict) -> None:
    """Complete or reopen a task in whichever backend is active."""
    if mode() == "live":
        client, err = _db()
        if err:
            st.error(err)
            return
        from db import queries
        uid = queries.current_user_id(client)
        if task.get("status") == "done":
            queries.set_task_status(client, task=task, status="todo", user_id=uid)
        else:
            queries.set_task_status(client, task=task, status="done", user_id=uid)
        st.cache_resource.clear()
    if task.get("status") == "done":
        reopen_task(task)
    else:
        complete_task(task)


def save_task_changes(task: dict, changes: dict) -> None:
    if mode() == "live":
        client, err = _db()
        if err:
            st.error(err)
            return
        from db import queries
        uid = queries.current_user_id(client)
        queries.update_task_fields(client, task=task, changes=changes, user_id=uid)
        st.cache_resource.clear()
    else:
        update_task(task, changes)


def create_task(fields: dict) -> None:
    if mode() == "live":
        client, err = _db()
        if err:
            st.error(err)
            return
        from db import queries
        uid = queries.current_user_id(client)
        queries.add_task(
            client, title=fields["title"], user_id=uid,
            notes=fields.get("notes", ""),
            priority_band=fields.get("priority_band", "medium"),
            impact=int(fields.get("impact", 3)), effort=int(fields.get("effort", 3)),
            estimated_minutes=int(fields.get("estimated_minutes", 30)),
            due_date=fields.get("due_date"))
        st.cache_resource.clear()
    else:
        add_task(fields)


def remove_task(task: dict) -> None:
    if mode() == "live":
        client, err = _db()
        if err:
            st.error(err)
            return
        from db import queries
        uid = queries.current_user_id(client)
        queries.delete_task(client, task=task, user_id=uid)
        st.cache_resource.clear()
    delete_task(task)
