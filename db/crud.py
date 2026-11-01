"""Generic CRUD for user-owned tables.

Instead of ten near-identical CRUD module files, tables with the standard
shape (id uuid PK + user_id ownership) share ONE implementation. Special
behaviour (task scoring, plan scheduling) stays in queries.py.

Every mutation writes an activity_logs row — audit trail is never optional.
"""
from datetime import date

from supabase import Client

# table -> (entity_type for activity_logs, allowed create/update fields)
ENTITIES = {
    "goals": ("goal", {"title", "description", "horizon", "target_date",
                        "status", "progress_pct"}),
    "projects": ("project", {"name", "description", "github_url", "blog_url",
                              "start_date", "target_date", "status", "blockers", "notes"}),
    "milestones": ("milestone", {"title", "position", "due_date", "status", "blocker"}),
    "skills": ("skill", {"name", "category", "current_level", "target_level",
                          "minutes_goal_weekly", "status", "notes"}),
    "weekly_reviews": ("review", {"week_start_date", "wins", "challenges",
                                   "planned_minutes", "actual_minutes", "tasks_done",
                                   "ai_summary"}),
    "english_logs": ("english", {"skill_id", "practice_type", "minutes",
                                  "confidence", "notes", "logged_on"}),
}

# 1:1 tables (PK = user_id) keep their PK column on insert
ONE_TO_ONE_TABLES = {"user_settings", "job_readiness"}


_DATE_COLUMNS = {"target_date", "start_date", "due_date", "week_start_date", "logged_on"}
_INT_COLUMNS = {"progress_pct", "current_level", "target_level", "minutes_goal_weekly",
                "planned_minutes", "actual_minutes", "tasks_done", "minutes",
                "confidence", "position"}


def _coerce(table: str, row: dict) -> dict:
    """Filter to allowed fields + normalise types (dates -> iso, ints -> int)."""
    allowed = ENTITIES[table][1] if table in ENTITIES else None
    out = {}
    for k, v in row.items():
        if allowed is not None and k not in allowed:
            continue
        if v is None or v == "":
            continue
        if k in _DATE_COLUMNS and not isinstance(v, str):
            out[k] = v.isoformat()
        elif k in _INT_COLUMNS:
            out[k] = int(v)
        else:
            out[k] = v
    return out


def list_rows(client: Client, table: str, *, order_by: str | None = None,
              desc: bool = False, filters: dict | None = None) -> list[dict]:
    q = client.table(table).select("*")
    for col, val in (filters or {}).items():
        if isinstance(val, (list, tuple, set)):
            q = q.in_(col, list(val))
        else:
            q = q.eq(col, val)
    if order_by:
        q = q.order(order_by, desc=desc)
    res = q.execute()
    return res.data or []


def insert_row(client: Client, table: str, row: dict, *, user_id: str) -> dict:
    """Create a row for the signed-in user; logs 'create' to activity_logs."""
    from db.queries import log_activity  # dodges circular import
    payload = _coerce(table, row)
    payload["user_id"] = user_id
    res = client.table(table).insert(payload).execute()
    created = res.data[0]
    entity_type = ENTITIES[table][0] if table in ENTITIES else table
    log_activity(client, user_id=user_id, entity_type=entity_type,
                 entity_id=created.get("id"), action="create",
                 detail={"fields": sorted(k for k in payload if k != 'user_id')})
    return created


def update_row(client: Client, table: str, row_id: str, changes: dict,
               *, user_id: str) -> dict:
    """Update allowed fields of an existing row; logs 'update'.

    For 1:1 tables (user_settings, job_readiness) `row_id` IS the user_id,
    because their primary key is user_id.
    """
    from db.queries import log_activity
    id_col = "user_id" if table in ONE_TO_ONE_TABLES else "id"
    clean = _coerce(table, changes)
    if not clean:
        raise ValueError("No valid fields provided to update")
    res = client.table(table).update(clean).eq(id_col, row_id).execute()
    if not res.data:  # row missing -> create it from the changes (upsert)
        res = client.table(table).insert({**clean, "user_id": user_id}).execute()
    updated = res.data[0]
    entity_type = ENTITIES[table][0] if table in ENTITIES else table
    log_activity(client, user_id=user_id, entity_type=entity_type,
                 entity_id=row_id, action="update",
                 detail={"changes": {k: str(v) for k, v in clean.items()}})
    return updated


def delete_row(client: Client, table: str, row_id: str, *, user_id: str,
               label: str = "") -> None:
    """Hard delete a row; logs 'delete' (nothing vanishes silently)."""
    from db.queries import log_activity
    client.table(table).delete().eq("id", row_id).execute()
    entity_type = ENTITIES[table][0] if table in ENTITIES else table
    log_activity(client, user_id=user_id, entity_type=entity_type,
                 entity_id=row_id, action="delete", detail={"label": label})
