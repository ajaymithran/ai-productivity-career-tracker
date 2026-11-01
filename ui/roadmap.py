"""Career Roadmap — goals, job readiness, resume/portfolio progress."""
from datetime import date, timedelta

import streamlit as st

from db import crud
from ui.components.ui_kit import empty_state, kpi_card, status_badge


@st.cache_resource
def _sup():
    from db.client import get_supabase
    return get_supabase()


def _readiness_upsert(client, uid: str) -> dict:
    """Ensure the 1:1 job_readiness row exists and return it."""
    rows = crud.list_rows(client, "job_readiness")
    return rows[0] if rows else {"user_id": uid, "resume_progress_pct": 0,
                                 "portfolio_progress_pct": 0,
                                 "readiness_score": 0, "applications_sent": 0,
                                 "interviews": 0, "target_role": None, "notes": None}


def render() -> None:
    st.header("🧭 Career Roadmap")
    st.caption("Where you want to go, and how close you already are.")

    client, err = _sup()
    if err:
        st.warning(err)
        return
    from db import queries
    uid = queries.current_user_id(client)

    jr = _readiness_upsert(client, uid)
    score = int(0.45 * jr.get("resume_progress_pct", 0)
                + 0.35 * jr.get("portfolio_progress_pct", 0)
                + 0.20 * min(jr.get("applications_sent", 0) * 5, 100))
    if score != jr.get("readiness_score"):
        crud.update_row(client, "job_readiness", uid, {"readiness_score": score}, user_id=uid)

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "Job readiness", f"{score}%", "resume+portfolio+apps")
    kpi_card(c2, "Resume done", f"{jr.get('resume_progress_pct',0)}%", "polished & targeted")
    kpi_card(c3, "Portfolio done", f"{jr.get('portfolio_progress_pct',0)}%", "public projects")
    kpi_card(c4, "Applications", jr.get("applications_sent", 0),
             f"{jr.get('interviews',0)} interview(s)")

    st.divider()
    left, right = st.columns([3, 2])

    with left:
        st.subheader("🎯 Goals")
        with st.form("addgoal", border=True, clear_on_submit=True):
            title = st.text_input("Goal", placeholder="e.g. Land a data analyst role")
            c1, c2 = st.columns(2)
            horizon = c1.select_slider("Horizon", ["short_term", "mid_term", "long_term"])
            target = c2.date_input("Target date", value=None,
                                   min_value=date.today())
            if st.form_submit_button("Add goal", type="primary") and title.strip():
                crud.insert_row(client, "goals",
                                {"title": title.strip(), "horizon": horizon,
                                 "target_date": target if target else None,
                                 "status": "active", "progress_pct": 0}, user_id=uid)
                st.rerun()

        goals = crud.list_rows(client, "goals", order_by="target_date")
        if not goals:
            empty_state("No goals yet. Name the destination; the planner fills the road.", "🧭")
        for g in goals:
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 1.8, 1.6])
                c1.markdown(f"**{g['title']}** {status_badge(g['status'])}<br>"
                            f"<sub>{g['horizon']} · due {str(g.get('target_date') or '—')[:10]}</sub>",
                            unsafe_allow_html=True)
                prog = c2.slider("Progress %", 0, 100, g.get("progress_pct", 0),
                                 key=f"gp_{g['id']}")
                if prog != g.get("progress_pct", 0):
                    if c3.button("Save", key=f"gs_{g['id']}"):
                        stat = "achieved" if prog == 100 and g["status"] == "active" else g["status"]
                        crud.update_row(client, "goals", g["id"],
                                        {"progress_pct": prog, "status": stat}, user_id=uid)
                        st.rerun()
                with c3.popover("✎", use_container_width=True):
                    act = st.select_slider("Status", ["active", "paused", "achieved", "abandoned"],
                                           g["status"], key=f"gact_{g['id']}")
                    if st.button("Apply", key=f"gap_{g['id']}"):
                        crud.update_row(client, "goals", g["id"], {"status": act}, user_id=uid)
                        st.rerun()
                    if st.button("🗑 Delete", key=f"gdel_{g['id']}"):
                        crud.delete_row(client, "goals", g["id"], user_id=uid, label=g["title"])
                        st.rerun()

    with right:
        st.subheader("📝 Weekly review")
        monday = date.today() - timedelta(days=date.today().weekday())
        reviews = crud.list_rows(client, "weekly_reviews", order_by="week_start_date", desc=True)
        this = next((r for r in reviews if str(r["week_start_date"])[:10] == monday.isoformat()), None)
        with st.form("weekly", border=True):
            st.caption(f"Week of {monday.isoformat()}")
            wins = st.text_area("Wins", (this or {}).get("wins") or "")
            chal = st.text_area("Challenges", (this or {}).get("challenges") or "")
            c1, c2, c3 = st.columns(3)
            planned = c1.number_input("Planned min", 0, 10000, (this or {}).get("planned_minutes") or 0)
            actual = c2.number_input("Actual min", 0, 10000, (this or {}).get("actual_minutes") or 0)
            tdone = c3.number_input("Tasks done", 0, 500, (this or {}).get("tasks_done") or 0)
            if st.form_submit_button("Save review", type="primary"):
                payload = {"wins": wins or None, "challenges": chal or None,
                           "planned_minutes": int(planned), "actual_minutes": int(actual),
                           "tasks_done": int(tdone)}
                if this:
                    crud.update_row(client, "weekly_reviews", this["id"], payload, user_id=uid)
                else:
                    crud.insert_row(client, "weekly_reviews",
                                    {**payload, "week_start_date": monday}, user_id=uid)
                st.success("Review saved.")
                st.rerun()
        if reviews:
            st.caption("Recent reviews")
            for r in reviews[:4]:
                st.markdown(f"- **{str(r['week_start_date'])[:10]}** — "
                            f"{r.get('actual_minutes',0) or 0}/{r.get('planned_minutes',0) or 0} min, "
                            f"{r.get('tasks_done',0) or 0} tasks")

        st.subheader("📄 Job readiness")
        with st.form("ready", border=True):
            role = st.text_input("Target role", jr.get("target_role") or "",
                                 placeholder="e.g. Junior Data Analyst")
            a = st.slider("Resume progress %", 0, 100, jr.get("resume_progress_pct", 0))
            b = st.slider("Portfolio progress %", 0, 100, jr.get("portfolio_progress_pct", 0))
            apps = st.number_input("Applications sent", 0, 999,
                                   jr.get("applications_sent", 0))
            ints = st.number_input("Interviews so far", 0, 99, jr.get("interviews", 0))
            note = st.text_area("Strategy notes", jr.get("notes") or "")
            if st.form_submit_button("Save readiness", type="primary"):
                crud.update_row(client, "job_readiness", uid,
                                {"target_role": role or None, "resume_progress_pct": a,
                                 "portfolio_progress_pct": b,
                                 "applications_sent": int(apps),
                                 "interviews": int(ints), "notes": note or None},
                                user_id=uid)
                st.rerun()
