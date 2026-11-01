"""Local SQLite persistence adapter — the 'works with zero credentials, still
persists' mode. Distinct from demo (session-memory) and live (Supabase).

Design:
  * stdlib sqlite3 only — no new dependency
  * schema mirrors the subset the UI mutates locally (tasks, settings,
    decision history, notifications)
  * every task row gets a uuid id; user_id fixed to 'local-user'
  * created/updated timestamps mirror the cloud schema conventions
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "tracker_local.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    notes TEXT,
    priority_band TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority_band IN ('low','medium','high','critical')),
    impact INTEGER NOT NULL DEFAULT 3 CHECK (impact BETWEEN 1 AND 5),
    effort INTEGER NOT NULL DEFAULT 3 CHECK (effort BETWEEN 1 AND 5),
    priority_score REAL NOT NULL DEFAULT 0,
    estimated_minutes INTEGER NOT NULL DEFAULT 30 CHECK (estimated_minutes BETWEEN 5 AND 600),
    due_date TEXT,
    status TEXT NOT NULL DEFAULT 'backlog'
        CHECK (status IN ('backlog','todo','in_progress','completed','cancelled')),
    project_id TEXT,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    proposal_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('approve','reject','edit')),
    notes TEXT,
    decided_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    notif_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    title TEXT NOT NULL,
    body TEXT,
    route TEXT,
    is_read INTEGER NOT NULL DEFAULT 0,
    read_at TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS english_logs (
    id TEXT PRIMARY KEY,
    practice_type TEXT NOT NULL,
    minutes INTEGER NOT NULL CHECK (minutes BETWEEN 1 AND 300),
    confidence INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 5),
    notes TEXT,
    logged_on TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(SCHEMA)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ----------------------------------------------------------------- tasks

def list_tasks(active_only: bool = True) -> list[dict]:
    init_db()
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM tasks").fetchall()
    tasks = [dict(r) for r in rows]
    for t in tasks:
        t["priority_score"] = t["priority_score"] or 0
    if active_only:
        tasks = [t for t in tasks if t["status"] not in ("completed", "cancelled")]
    return tasks


def insert_task(fields: dict) -> dict:
    init_db()
    from core.priority import compute_priority_score
    task = {
        "id": str(uuid.uuid4()),
        "title": fields["title"].strip(),
        "notes": fields.get("notes") or "",
        "priority_band": fields.get("priority_band", "medium"),
        "impact": int(fields.get("impact", 3)),
        "effort": int(fields.get("effort", 3)),
        "priority_score": compute_priority_score(
            impact=int(fields.get("impact", 3)), effort=int(fields.get("effort", 3)),
            priority_band=fields.get("priority_band", "medium"),
            due_date=fields.get("due_date")),
        "estimated_minutes": int(fields.get("estimated_minutes", 30)),
        "due_date": fields.get("due_date").isoformat() if fields.get("due_date") else None,
        "status": fields.get("status", "todo"),
        "completed_at": None,
        "created_at": _now(), "updated_at": _now(),
    }
    with _connect() as conn:
        conn.execute(
            "INSERT INTO tasks (id,title,notes,priority_band,impact,effort,priority_score,"
            "estimated_minutes,due_date,status,completed_at,created_at,updated_at) "
            "VALUES (:id,:title,:notes,:priority_band,:impact,:effort,:priority_score,"
            ":estimated_minutes,:due_date,:status,:completed_at,:created_at,:updated_at)",
            task)
    return task


def update_task(task_id: str, changes: dict) -> dict | None:
    init_db()
    allowed = {"title", "notes", "priority_band", "impact", "effort",
               "estimated_minutes", "due_date", "status"}
    clean = {k: v for k, v in changes.items() if k in allowed}
    if not clean:
        return None
    if "due_date" in clean and hasattr(clean["due_date"], "isoformat"):
        clean["due_date"] = clean["due_date"].isoformat()
    clean["updated_at"] = _now()
    if clean.get("status") == "completed":
        clean["completed_at"] = _now()
    sets = ", ".join(f"{k}=?" for k in clean) 
    with _connect() as conn:
        conn.execute(f"UPDATE tasks SET {sets} WHERE id=?", [*clean.values(), task_id])
    return _get_task(task_id)


def set_status(task_id: str, status: str) -> dict | None:
    init_db()
    if status not in ("backlog", "todo", "in_progress", "completed", "cancelled"):
        raise ValueError(f"invalid status {status}")
    return update_task(task_id, {"status": status})


def _get_task(task_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    return dict(row) if row else None


def delete_task(task_id: str) -> None:
    init_db()
    with _connect() as conn:
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))


# ------------------------------------------------------------- settings

def get_setting_json(key: str, default=None):
    init_db()
    with _connect() as conn:
        row = conn.execute("SELECT value FROM app_settings WHERE key=?", (key,)).fetchone()
    return json.loads(row["value"]) if row else default


def set_setting_json(key: str, value) -> None:
    init_db()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO app_settings (key,value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)))


# ------------------------------------------------- approval / decision history

def record_decision(proposal_id: str, action: str, notes: str = "") -> str:
    init_db()
    if action not in ("approve", "reject", "edit"):
        raise ValueError(f"invalid action {action}")
    did = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO decisions (id,proposal_id,action,notes,decided_at) VALUES (?,?,?,?,?)",
            (did, proposal_id, action, notes, _now()))
    return did


def list_decisions(limit: int = 20) -> list[dict]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM decisions ORDER BY decided_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


# ------------------------------------------------------ notifications (idempotent)

def create_notification(notif_type: str, severity: str, title: str,
                        body: str = "", route: str = "") -> bool:
    """Idempotent by (type, title, created-day): retries never duplicate."""
    init_db()
    key_like = f"{notif_type}%{title}%{date.today().isoformat()}%"
    with _connect() as conn:
        dup = conn.execute(
            "SELECT 1 FROM notifications WHERE notif_type=? AND title=? "
            "AND substr(created_at,1,10)=?",
            (notif_type, title, date.today().isoformat())).fetchone()
        if dup:
            return False
        conn.execute(
            "INSERT INTO notifications (id,notif_type,severity,title,body,route,created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), notif_type, severity, title, body, route, _now()))
    return True


def list_notifications() -> list[dict]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM notifications ORDER BY created_at DESC LIMIT 50").fetchall()
    out = [dict(r) for r in rows]
    for n in out:
        n["is_read"] = bool(n["is_read"])
    return out


def mark_read(notification_id: str) -> None:
    init_db()
    with _connect() as conn:
        conn.execute(
            "UPDATE notifications SET is_read=1, read_at=? WHERE id=?",
            (_now(), notification_id))


# ------------------------------------------------------ english logs

def insert_english_log(fields: dict) -> str:
    init_db()
    rid = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO english_logs (id,practice_type,minutes,confidence,notes,logged_on,created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (rid, fields["practice_type"], int(fields["minutes"]),
             int(fields.get("confidence", 3)), fields.get("notes"),
             fields.get("logged_on") or date.today().isoformat(), _now()))
    return rid


def list_english_logs(limit: int = 30) -> list[dict]:
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM english_logs ORDER BY logged_on DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]
