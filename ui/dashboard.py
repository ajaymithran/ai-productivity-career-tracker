"""Dashboard — today's command center.

Everything here is deterministic: KPI cards, top priorities, deadline
notices, skill-gap snapshot. AI never writes here.
"""
from datetime import date

import streamlit as st

from db import crud
from ui.components.ui_kit import empty_state, kpi_card, notice_row


@st.cache_resource
def _sup():
    from db.client import get_supabase
    return get_supabase()


def _uid(client):
    from db import queries
    return queries.current_user_id(client)


def _render_deadline_notices(tasks: list[dict]) -> None:
    """In-app notices computed live (never e-mail, per design)."""
    tiso = date.today().isoformat()
    notices = []
    for t in tasks:
        dd = str(t.get("due_date") or "")[:10]
        if not dd or t.get("status") in ("done", "wont_do"):
            continue
        days = (date.fromisoformat(dd) - date.today()).days
        if days < 0:
            notices.append(("urgent", f"'{t['title']}' is {-days} day(s) overdue", dd))
        elif days == 0:
            notices.append(("warning", f"'{t['title']}' is due TODAY", dd))
        elif days <= 3:
            notices.append(("info", f"'{t['title']}' due in {days} days", dd))
    if notices:
        st.markdown("###### 🔔 Today's notices")
        for sev, text, dd in notices[:6]:
            notice_row(sev, text + f" — due {dd}")
    # unread stored notifications (e.g. from scheduled jobs)
    try:
        client, _ = _sup()
        unread = crud.list_rows(client, "notifications",
                                filters={"is_read": False}, order_by="created_at", desc=True)
        for n in unread[:4]:
            notice_row(n.get("severity", "info"), f"[{n.get('notif_type','system')}] {n.get('title','')}")
    except Exception:
        pass


def render() -> None:
    st.header("📊 Dashboard")
    st.caption(f"Snapshot for {date.today().strftime('%A, %d %B %Y')}")

    client, err = _sup()
    if err:
        st.warning(err)
        return
    uid = _uid(client)

    tasks = crud.list_rows(client, "tasks", order_by="priority_score", desc=True)
    skills = crud.list_rows(client, "skills", order_by="name")
    goals = crud.list_rows(client, "goals", order_by="target_date")

    tiso = date.today().isoformat()
    open_tasks = [t for t in tasks if t.get("status") not in ("done", "wont_do")]
    overdue = [t for t in open_tasks if t.get("due_date") and str(t["due_date"])[:10] < tiso]
    today_t = [t for t in open_tasks if t.get("due_date") and str(t["due_date"])[:10] == tiso]
    done_recent = [t for t in tasks if t.get("status") == "done"
                   and str(t.get("completed_at") or "")[:10] == tiso]
    today_minutes = sum(int(t.get("estimated_minutes", 0)) for t in overdue + today_t)

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Open tasks", len(open_tasks), "all lists")
    kpi_card(c2, "Overdue", len(overdue), "needs triage" if overdue else "clean 🎉")
    kpi_card(c3, "Today's load", f"{today_minutes} min", "overdue+today")
    kpi_card(c4, "Done today", len(done_recent), "keep the streak")

    st.divider()
    left, right = st.columns([3, 2])

    with left:
        st.markdown("###### 🎯 Top priorities (Python-scored)")
        pool = [t for t in open_tasks if (t.get("due_date") and str(t['due_date'])[:10] <= tiso)][:6]
        pool = pool or [t for t in open_tasks][:6]
        if not pool:
            empty_state("No open tasks. Add your first one in the 🗓 Daily Planner.")
        for t in pool:
            dd = str(t.get("due_date") or "—")[:10]
            st.markdown(
                f"- **{t['title']}** — `{t['priority_score']}` · {t['estimated_minutes']} min · due {dd}"
            )
        _render_deadline_notices(open_tasks)

    with right:
        st.markdown("###### 🧠 Active skill focus")
        active_skills = [s for s in skills if s.get("status") == "active"]
        if not active_skills:
            empty_state("No skills tracked yet — add them in 🧠 Skills.")
        for s in active_skills[:6]:
            lvl = s.get("current_level", 0)
            tgt = s.get("target_level", 5)
            st.markdown(f"**{s['name']}**")
            st.progress(min(lvl / max(tgt, 1), 1.0),
                        text=f"level {lvl} → target {tgt}")
        st.markdown("###### 🧭 Active goals")
        active_goals = [g for g in goals if g.get("status") == "active"]
        if not active_goals:
            empty_state("No goals yet — set one in 🧭 Career Roadmap.")
        for g in active_goals[:4]:
            st.markdown(f"- **{g['title']}** — {g.get('progress_pct',0)}% · due {str(g.get('target_date') or '—')[:10]}")
