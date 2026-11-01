"""Daily Planner — task CRUD against live Supabase.

Data path: form -> queries.add_task -> RLS checks session -> row saved
(+ activity_logs audit row). Python computes priority; no AI anywhere here.
"""
from datetime import date, timedelta

import streamlit as st

from db import crud
from db import queries
from db.client import get_supabase


@st.cache_resource
def _sup():
    """Cache the authenticated client for the whole browser session."""
    return get_supabase()


def _status_badge(status: str) -> str:
    return {"todo": "◻️ Todo", "in_progress": "🔨 In progress",
            "done": "✅ Done", "wont_do": "🙈 Won't do"}.get(status, status)


def _due_note(due_date: str | None) -> str:
    if not due_date:
        return ""
    d = date.fromisoformat(str(due_date)[:10])
    days_left = (d - date.today()).days
    if days_left < 0:
        return f' :red[OVERDUE {-days_left}d]'
    if days_left == 0:
        return " :orange[TODAY]"
    if days_left <= 3:
        return f" :yellow[{days_left}d left]"
    return f" *( {days_left}d )*"


def _add_task_form(client) -> None:
    with st.form("add_task", border=True):
        st.subheader("➕ New task")
        title = st.text_input("Title", placeholder="e.g. Finish SQL joins module")
        c1, c2, c3 = st.columns(3)
        with c1:
            band = st.select_slider("Priority band", ["low", "medium", "high"], "medium")
        with c2:
            impact = st.slider("Impact", 1, 5, 3, help="How much does completing this matter?")
        with c3:
            effort = st.slider("Effort level", 1, 5, 3, help="5 = heavy grind")
        c4, c5 = st.columns(2)
        with c4:
            est = st.number_input("Estimated minutes", 5, 600, 30, 5)
        with c5:
            due = st.date_input("Due date", value=None, min_value=date.today() - timedelta(days=365))
        notes = st.text_area("Notes (optional)")

        if st.form_submit_button("Add task", type="primary", use_container_width=True):
            try:
                uid = queries.current_user_id(client)
                task = queries.add_task(
                    client, title=title, user_id=uid, notes=notes,
                    priority_band=band, impact=impact, effort=effort,
                    estimated_minutes=int(est), due_date=due,
                )
                st.success(f"Task added — priority {task['priority_score']} (Python-computed, not AI).")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not add task: {str(exc)[:200]}")


def _task_row(client, uid: str, task: dict) -> None:
    """One task rendered as a compact interactive row."""
    cols = st.columns([0.5, 5.0, 1.1, 1.1, 1.1])
    with cols[0]:
        st.markdown(f"### {int(task['priority_score'])}")
    with cols[1]:
        st.markdown(
            f"**{task['title']}**{_due_note(task.get('due_date'))}<br>"
            f"<sub>{task['priority_band']} · impact {task['impact']} · effort "
            f"{task['effort']} · {task['estimated_minutes']} min · {_status_badge(task['status'])}</sub>",
            unsafe_allow_html=True,
        )
    with cols[2]:
        if task["status"] != "done" and st.button("✓", key=f"done_{task['id']}",
                                                  help="Mark done", use_container_width=True):
            queries.set_task_status(client, task=task, status="done", user_id=uid)
            st.rerun()
    with cols[3]:
        edit_key = f"edit_{task['id']}"
        with st.popover("✎", use_container_width=True):
            new_title = st.text_input("Title", value=task["title"], key=f"t_{task['id']}")
            c1, c2 = st.columns(2)
            with c1:
                new_est = st.number_input("Minutes", 5, 600, task["estimated_minutes"],
                                          key=f"e_{task['id']}")
            with c2:
                new_band = st.select_slider("Band", ["low", "medium", "high"],
                                            task["priority_band"], key=f"b_{task['id']}")
            new_due = st.date_input("Due date", key=f"d_{task['id']}",
                                    value=date.fromisoformat(str(task["due_date"])[:10])
                                    if task.get("due_date") else None)
            if st.button("Save changes", type="primary", key=f"s_{task['id']}"):
                changes = {"title": new_title.strip() or task["title"],
                           "estimated_minutes": int(new_est),
                           "priority_band": new_band,
                           "due_date": new_due}
                queries.update_task_fields(client, task=task, changes=changes, user_id=uid)
                st.rerun()
    with cols[4]:
        with st.popover("🗑", use_container_width=True):
            st.write(f"Delete **{task['title']}** permanently?")
            if st.button("Yes, delete", key=f"delyes_{task['id']}"):
                queries.delete_task(client, task=task, user_id=uid)
                st.rerun()


def _group_tasks(client, uid: str, label: str, tasks: list[dict]) -> None:
    st.subheader(f"{label} ({len(tasks)})")
    if not tasks:
        st.caption("Nothing here — add a task above or enjoy the quiet.")
        return
    for task in tasks:
        _task_row(client, uid, task)


# --------------------------------------------------------------------------
# Time allocation: build today's plan respecting availability (Python decides)
# --------------------------------------------------------------------------
def _plan_section(client, uid: str) -> None:
    st.divider()
    st.subheader("🧩 Allocate today's time")
    settings_rows = crud.list_rows(client, "user_settings")
    availability = int(settings_rows[0].get("daily_study_minutes", 120)
                       if settings_rows else 120)

    existing = crud.list_rows(client, "daily_plans",
                              filters={"plan_date": date.today().isoformat()})
    if existing:
        plan = existing[0]
        items = crud.list_rows(client, "daily_plan_items",
                               filters={"plan_id": plan["id"]}, order_by="position")
        used = sum(int(i["minutes_allocated"]) for i in items)
        st.info(f"Plan for today exists — {used}/{availability} min allocated "
                f"({plan['status']})")
        for i in items:
            task_title = str(i.get("notes") or "Practice item")
            c1, c2 = st.columns([5, 1])
            st.markdown(f"- {task_title} — {i['minutes_allocated']} min")
            if c2.button("✕", key=f"rmi_{i['id']}", help="Remove from plan"):
                crud.delete_row(client, "daily_plan_items", i["id"], user_id=uid)
                st.rerun()
        if plan["status"] in ("draft", "active") and st.button("Mark plan COMPLETED",
                                                               key="done_plan"):
            client.table("daily_plans").update({"status": "completed"})\
                  .eq("id", plan["id"]).execute()
            st.rerun()
        return

    tasks = queries.fetch_open_tasks(client)
    if not tasks:
        st.caption("No open tasks to allocate.")
        return

    labels = {t["id"]: f"{t['title']} ({t['estimated_minutes']} min)"
              for t in tasks}
    picked = st.multiselect("Choose tasks for today (overdue first)",
                            list(labels.keys()),
                            format_func=lambda i: labels[i],
                            default=[t["id"] for t in tasks
                                     if str(t.get("due_date") or "")[:10]
                                     <= date.today().isoformat()][:5])
    chosen_minutes = sum(int(t["estimated_minutes"]) for t in tasks if t["id"] in picked)
    over = chosen_minutes > availability
    st.metric("Allocated", f"{chosen_minutes} / {availability} min",
              delta=f"{'+' if over else ''}{chosen_minutes - availability} vs availability",
              delta_color="inverse" if over else "off")
    if over:
        st.warning("Python validation: this exceeds today's availability. "
                   "Fix by unloading low-priority items before saving.")

    if st.button("💾 Save today's plan", type="primary", disabled=over) and picked:
        plan = client.table("daily_plans").insert({
            "user_id": uid, "plan_date": date.today().isoformat(),
            "availability_minutes": availability, "status": "active",
        }).execute().data[0]
        from db.queries import log_activity
        log_activity(client, user_id=uid, entity_type="plan", entity_id=plan["id"],
                     action="create", detail={"items": len(picked),
                                              "minutes": chosen_minutes})
        for pos, tid in enumerate(picked, 1):
            t = next(t for t in tasks if t["id"] == tid)
            crud.insert_row(client, "daily_plan_items",
                            {"plan_id": plan["id"], "task_id": tid,
                             "minutes_allocated": t["estimated_minutes"],
                             "position": pos,
                             "notes": t["title"]}, user_id=uid)
        st.rerun()


def render() -> None:
    st.header("🗓️ Daily Planner")
    st.caption("Create, order and finish today's work. Priority is computed "
               "deterministically by Python — same inputs, same score, always.")

    client, err = _sup()
    if err:
        st.warning(err)
        return

    _add_task_form(client)
    st.divider()

    uid = queries.current_user_id(client)
    tasks = queries.fetch_open_tasks(client)

    today_iso = date.today().isoformat()
    overdue = [t for t in tasks if t.get("due_date") and str(t["due_date"])[:10] < today_iso]
    today_t = [t for t in tasks if t.get("due_date") and str(t["due_date"])[:10] == today_iso]
    notime = [t for t in tasks if not t.get("due_date")]
    upcoming = [t for t in tasks if t.get("due_date")
                and str(t["due_date"])[:10] > today_iso]

    _group_tasks(client, uid, "⏰ Overdue", overdue)
    _group_tasks(client, uid, "☀️ Today", today_t)
    _group_tasks(client, uid, "📅 Upcoming", upcoming)
    _group_tasks(client, uid, "🗂 No date set", notime)
    _plan_section(client, uid)
