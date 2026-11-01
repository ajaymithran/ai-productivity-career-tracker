"""Data source abstraction — pages never know where data came from.

modes:
  * "live"  → Supabase (authenticated; RLS enforces ownership)
  * "local" → SQLite adapter (persistent across restarts, zero credentials)
  * "demo"  → session-memory sample data (clearly labelled, for previews)

Loaders return the same shape in all modes so pages stay identical.
Every mutation routes through this layer — pages never touch stores directly.
"""
from __future__ import annotations

import streamlit as st

import data.demo_data as demo
from data.demo_data import data as demo_data


def mode() -> str:
    from config.settings import settings
    if not (settings.supabase_configured() and settings.SUPABASE_USER_EMAIL
            and settings.SUPABASE_USER_PASSWORD):
        return "demo" if st.session_state.get("data_mode") == "demo" else "local"
    return st.session_state.get("data_mode", "live")


def banner() -> None:
    m = mode()
    if m == "demo":
        st.info("🧪 **Demo mode — sample data** (resets on refresh).")
    elif m == "local":
        st.caption(f"💾 **Local mode** — data persists in `tracker_local.db` "
                   "on your machine. Add Supabase `.env` credentials to go cloud.")


def _db():
    from db.client import get_supabase
    return get_supabase()


def _fallback_db(exc=None) -> dict:
    st.warning(f"Database unavailable ({str(exc)[:110] if exc else 'unknown'}) "
               "— falling back to demo data this render.")
    return demo_data()


# ------------------------------------------------------------------ loads

def load_user() -> dict:
    d = demo_data()
    if mode() == "live":
        try:
            client, err = _db()
            if err:
                return d["settings"]
            from db import crud
            rows = crud.list_rows(client, "user_settings")
            if rows:
                return d["settings"] | {k: rows[0].get(k) for k in
                                        ("daily_study_minutes", "study_start_time",
                                         "study_end_time", "weekly_review_day",
                                         "ai_enabled", "ai_tone")}
            return d["settings"]
        except Exception as exc:
            _fallback_db(exc)
            return d["settings"]
    if mode() == "local":
        from src.database import local_store as store
        base = d["settings"]
        saved = store.get_setting_json("user_settings", {})
        return {**base, **saved}
    return d["settings"]


def load_tasks(active_only: bool = True) -> list[dict]:
    d = demo_data()
    if mode() == "live":
        try:
            client, err = _db()
            if err:
                return _norm(d["tasks"])
            from db import crud
            tasks = crud.list_rows(client, "tasks")
        except Exception as exc:
            _fallback_db(exc)
            return _norm(d["tasks"])
    elif mode() == "local":
        from src.database import local_store as store
        tasks = store.list_tasks(active_only=False)
    else:
        tasks = d["tasks"]
    tasks = [dict(t) for t in tasks]
    for t in tasks:
        # one UI vocabulary everywhere: the store layer may say "completed"
        # (local SQLite CHECK constraint) but live/demo/UI all use "done"
        if t.get("status") == "completed":
            t["status"] = "done"
        t.setdefault("estimated_minutes", 30)
        t.setdefault("priority_score", 0)
        t.setdefault("priority_band", "medium")
    if active_only:
        tasks = [t for t in tasks if t.get("status") not in ("done", "completed", "cancelled",
                                                             "wont_do")]
    return tasks


def _norm(_rows: list) -> list:
    return demo_data()["tasks"]


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
    if mode() == "local":
        from src.database import local_store as store
        return store.list_english_logs()
    d = demo_data()
    return d["english_logs"]


def load_notifications() -> list[dict]:
    if mode() == "local":
        from src.database import local_store as store
        return [n for n in store.list_notifications() if not n["is_read"]]
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
    return load_user()


def load_proposals() -> list[dict]:
    d = demo_data()
    return d["ai_proposals"]


def load_decisions() -> list[dict]:
    """Approval history in the active store (local only so far)."""
    if mode() == "local":
        from src.database import local_store as store
        return store.list_decisions()
    if mode() == "live":
        try:
            client, err = _db()
            if err:
                return []
            from db import crud
            return crud.list_rows(client, "ai_proposals", order_by="created_at", desc=True)
        except Exception:
            return []
    return st.session_state.setdefault("decisions", [])


def load_decision_store():
    """The object the approvals service records into (store protocol)."""
    if mode() == "live":
        client, err = _db()
        if err:
            return None
        return _SupabaseApprovalStore(client)
    return _LocalApprovalStore()


class _LocalApprovalStore:
    def record_decision(self, proposal_id: str, action: str, notes: str = "") -> str:
        from src.database import local_store as store
        return store.record_decision(proposal_id, action, notes)

    def list_decisions(self, limit: int = 50) -> list[dict]:
        from src.database import local_store as store
        return store.list_decisions(limit)


class _SupabaseApprovalStore:
    def __init__(self, client):
        self._client = client

    def record_decision(self, proposal_id: str, action: str, notes: str = "") -> str:
        from db.queries import current_user_id, log_activity
        uid = current_user_id(self._client)
        status = {"approve": "approved", "reject": "rejected",
                  "edit": "edited"}[action]
        self._client.table("ai_proposals").update({
            "status": status,
            "applied_result": {"note": f"decision recorded: {action}",
                               "user_note": notes or None},
        }).eq("id", proposal_id).execute()
        log_activity(self._client, user_id=uid, entity_type="ai_proposal",
                     entity_id=proposal_id,
                     action="approve" if action == "approve" else
                     ("reject" if action == "reject" else "edit_before_apply"),
                     detail={"note": notes})
        return f"{proposal_id}:{action}"

    def list_decisions(self, limit: int = 50) -> list[dict]:
        rows = self._client.table("ai_proposals").select("*") \
            .neq("status", "pending").limit(limit).execute().data or []
        return [{"proposal_id": r["id"], "action": {"approved": "approve",
                 "rejected": "reject", "edited": "edit"}.get(r.get("status"), r["status"]),
                 "decided_at": str(r.get("updated_at"))} for r in rows]


# -------------------------------------------------------------- mutations

def toggle_task_done(task: dict) -> None:
    if mode() == "live":
        client, err = _db()
        if err:
            st.error(err)
            return
        from db import queries
        uid = queries.current_user_id(client)
        new_status = "todo" if task.get("status") == "done" else "done"
        queries.set_task_status(client, task=task, status=new_status, user_id=uid)
        st.cache_resource.clear()
        st.session_state.pop("tasks_cache", None)
    elif mode() == "local":
        from src.database import local_store as store
        new = "todo" if task.get("status") in ("done", "completed") else "completed"
        store.set_status(task["id"], new)
    else:
        if task.get("status") == "done":
            reopen_task(task)
        else:
            complete_task(task)
    _tasks_changed()


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
    elif mode() == "local":
        from src.database import local_store as store
        store.update_task(task["id"], changes)
    else:
        update_task(task, changes)
    _tasks_changed()


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
    elif mode() == "local":
        from src.database import local_store as store
        store.insert_task(fields)
    else:
        add_task(fields)
    _tasks_changed()


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
    elif mode() == "local":
        from src.database import local_store as store
        store.delete_task(task["id"])
    else:
        delete_task(task)
    _tasks_changed()


def log_english_log(fields: dict) -> None:
    if mode() == "local":
        from src.database import local_store as store
        store.insert_english_log(fields)
        return
    st.info("English logging persists in live/local modes; demo keeps session only.")


def record_app_decision(proposal_id: str, action: str, notes: str = "") -> dict | None:
    """UI-facing approval recording via the approvals service."""
    from src.services import approvals
    store = load_decision_store()
    if store is None:
        st.warning("Approval recording needs a configured backend (local or Supabase).")
        return None
    return approvals.record_decision(store, proposal_id=proposal_id,
                                     action=action, notes=notes)


def _tasks_changed() -> None:
    """Event hook for automation: analytics + notices refresh on data changes."""
    if mode() == "local":
        try:
            from automation import workflows
            workflows.deadline_notifications(_LocalMutationStore())
        except Exception:
            pass


class _LocalMutationStore:
    """Adapter exposing the local store under the workflows protocol."""

    def list_tasks(self, active_only: bool = True) -> list[dict]:
        from src.database import local_store as store
        return store.list_tasks(active_only=active_only)

    def create_notification(self, notif_type: str, severity: str, title: str,
                            body: str = "", route: str = "") -> bool:
        from src.database import local_store as store
        return store.create_notification(notif_type, severity, title, body, route)


# ------------------------------------------------- demo-mode mutators (kept)

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
