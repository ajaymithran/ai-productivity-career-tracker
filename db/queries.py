"""All database table operations live here — CRUD layer.

Rules:
  * UI pages never build their own .table(...) chains; they call these.
  * Every mutation writes an activity_logs row (audit trail).
  * Functions receive the authenticated client from db.client.get_supabase();
    RLS therefore always scopes rows to the signed-in user.
"""
from datetime import date, datetime, timezone

from supabase import Client

from core.priority import compute_priority_score

ACTIVITY_ACTIONS = ("create", "update", "delete", "status_change")


def current_user_id(client: Client) -> str:
    """Return the signed-in user's id (profiles.id)."""
    return client.auth.get_user().user.id


def log_activity(
    client: Client,
    *,
    entity_type: str,
    entity_id: str | None,
    action: str,
    user_id: str,
    detail: dict | None = None,
) -> None:
    """Append an audit row. 'Who changed what, when' - never optional."""
    payload = {
        "user_id": user_id,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "action": action,
        "detail": detail or {},
    }
    res = client.table("activity_logs").insert(payload).execute()
    if res.data is None:
        raise RuntimeError("activity_logs insert failed")


# ---------------------------------------------------------------- tasks CRUD

def add_task(
    client: Client,
    *,
    title: str,
    user_id: str,
    notes: str = "",
    priority_band: str = "medium",
    impact: int = 3,
    effort: int = 3,
    estimated_minutes: int = 30,
    due_date: date | None = None,
    project_id: str | None = None,
    milestone_id: str | None = None,
    goal_id: str | None = None,
) -> dict:
    """Create a task. priority_score is computed by Python (not AI)."""
    if not (title and title.strip()):
        raise ValueError("Task title must not be empty")
    title = title.strip()

    score = compute_priority_score(
        impact=impact, effort=effort, priority_band=priority_band, due_date=due_date
    )

    payload = {
        "user_id": user_id,
        "title": title,
        "notes": notes.strip() or None,
        "priority_band": priority_band,
        "impact": impact,
        "effort": effort,
        "priority_score": score,
        "estimated_minutes": estimated_minutes,
        "due_date": due_date.isoformat() if due_date else None,
        "project_id": project_id,
        "milestone_id": milestone_id,
        "goal_id": goal_id,
    }
    res = client.table("tasks").insert(payload).execute()
    task = res.data[0]

    log_activity(
        client, user_id=user_id, entity_type="task", entity_id=task["id"],
        action="create", detail={"title": title, "priority_score": score},
    )
    return task


def fetch_open_tasks(client: Client) -> list[dict]:
    """All tasks not done/wont_do; top priority first."""
    res = (
        client.table("tasks")
        .select("*")
        .in_("status", ["todo", "in_progress"])
        .order("priority_score", desc=True)
        .execute()
    )
    return res.data or []


def update_task_fields(client: Client, *, task: dict, changes: dict, user_id: str) -> dict:
    """Update allowed fields only. Changes shape: {field: new_value}."""
    allowed = {"title", "notes", "priority_band", "impact", "effort",
               "estimated_minutes", "due_date", "status"}
    bad = set(changes) - allowed
    if bad:
        raise ValueError(f"Fields not editable here: {sorted(bad)}")

    # keep priority_score consistent with any scoring inputs that changed
    if {"impact", "effort", "priority_band", "due_date"} & set(changes):
        merged = {
            "impact": changes.get("impact", task["impact"]),
            "effort": changes.get("effort", task["effort"]),
            "priority_band": changes.get("priority_band", task["priority_band"]),
            "due_date": changes.get("due_date", task["due_date"]),
        }
        changes["priority_score"] = compute_priority_score(
            impact=merged["impact"],
            effort=merged["effort"],
            priority_band=merged["priority_band"],
            due_date=merged["due_date"],
        )

    if "due_date" in changes and changes["due_date"]:
        changes["due_date"] = changes["due_date"].isoformat()[:10]

    res = client.table("tasks").update(changes).eq("id", task["id"]).execute()
    updated = res.data[0]

    log_activity(
        client, user_id=user_id, entity_type="task", entity_id=task["id"],
        action="update", detail={"changes": {k: str(v) for k, v in changes.items()}},
    )
    return updated


def set_task_status(client: Client, *, task: dict, status: str, user_id: str) -> dict:
    """Move a task between statuses; stamps completed_at for 'done'."""
    if status not in ("todo", "in_progress", "done", "wont_do"):
        raise ValueError(f"Invalid status: {status}")

    changes: dict = {"status": status}
    if status == "done":
        # REST inserts must carry a real timestamp (no server-side 'now()')
        changes["completed_at"] = datetime.now(timezone.utc).isoformat()
    elif task.get("status") == "done" and status in ("todo", "in_progress"):
        changes["completed_at"] = None

    res = client.table("tasks").update(changes).eq("id", task["id"]).execute()
    updated = res.data[0]

    log_activity(
        client, user_id=user_id, entity_type="task", entity_id=task["id"],
        action="status_change",
        detail={"from": task["status"], "to": status},
    )
    return updated


def delete_task(client: Client, *, task: dict, user_id: str) -> None:
    """Delete is allowed but ALWAYS logged (what was lost, when)."""
    client.table("tasks").delete().eq("id", task["id"]).execute()
    log_activity(
        client, user_id=user_id, entity_type="task", entity_id=task["id"],
        action="delete", detail={"title": task["title"]},
    )
