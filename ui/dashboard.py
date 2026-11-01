"""PAGE 1 — Dashboard: welcome, daily focus, KPIs, checklist, AI card, trends."""
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data.demo_data as demo
import data.source as source
from core.scheduler import deadline_notice_level, select_for_today
from ui.components import ui_kit as kit
from ui.design import TOKENS


@st.cache_resource
def _sup():
    from db.client import get_supabase
    return get_supabase()


def _ai_daily_card(tasks: list[dict], availability: int) -> None:
    """Deterministic plan (Python) presented with Approve/Edit/Reject."""
    plan = select_for_today(tasks, availability)
    used = sum(int(t.get("estimated_minutes", 0)) for t in plan)
    if plan:
        body = "\n".join(
            f"{i}. {t['title']} — {t['estimated_minutes']} min "
            f"({'overdue' if str(t.get('due_date') or '')[:10] < date.today().isoformat() else 'next'})"
            for i, t in enumerate(plan, 1))
        reason = (f"Python sorted overdue first, then highest priority_score; "
                  f"{used}/{availability} min fits your availability.")
    else:
        body = "No open tasks to plan — add some in the Daily Planner."
        reason = "Empty list, empty plan."
    with st.container():
        kit.ai_card("Today's recommended plan (deterministic)", body, reason,
                    footer_meta="Approve records your decision — your tasks are "
                                "never touched without your click.",
                    key="dash_ai")
        if used > availability:
            st.warning(f"Overload check: {used} min > {availability} min availability.")
        kit.consume_ai_decision("dash_ai", "dash_daily_plan")


def render() -> None:
    st.markdown(ui_header := "", unsafe_allow_html=True)
    profile = source.load_user()
    settings = source.load_settings()
    tasks_all = source.load_tasks(active_only=False)
    tasks = source.load_tasks(active_only=True)
    projects = source.load_projects()
    goals = source.load_goals() if True else []
    skills = source.load_skills()
    notifications = source.load_notifications()

    today = date.today()
    tiso = today.isoformat()
    kit.page_header(
        f"Good day, {profile.get('display_name','there')} 👋",
        "Your command center for today",
        primary_action=("＋ New task", "dash_new"),
        date_context=today.strftime("%A, %d %B %Y"),
    )
    if kit.header_action_pressed("dash_new"):
        st.session_state["show_dash_form"] = not st.session_state.get("show_dash_form", False)
    kit.page_banner_demo()

    if st.session_state.get("show_dash_form"):
        with st.container():
            kit.add_task_form("dash", default_due=today)
        st.divider()

    # notifications strip
    if notifications:
        with st.expander(f"🔔 Notifications ({len(notifications)})", expanded=False):
            for n in notifications[:5]:
                kit.notice(n.get("severity", "info"), n.get("title", ""))

    # daily focus
    with st.container():
        st.markdown("### 🎯 Daily focus")
        overdue = [t for t in tasks if t.get("due_date") and str(t["due_date"])[:10] < tiso]
        focus = select_for_today(tasks, int(settings.get("daily_study_minutes", 120)))
        if focus:
            st.markdown(
                f"**{focus[0]['title']}** first, then {max(len(focus)-1,0)} more — "
                f"{sum(int(t.get('estimated_minutes',0)) for t in focus)} min planned "
                f"of {settings.get('daily_study_minutes',120)} available."
            )
        else:
            st.markdown("Nothing scheduled — enjoy, or plan ahead.")

    # KPIs — honest, sample-labelled
    done_today = [t for t in tasks_all if t.get("status") == "done"
                  and str(t.get("completed_at") or "")[:10] == tiso]
    today_minutes = sum(int(t.get("estimated_minutes", 0)) for t in done_today)
    active_projects = [p for p in projects if p.get("status") not in ("done", "dropped")]
    on_track = [g for g in goals if g.get("status") == "active"
                and (g.get("progress_pct", 0) or 0) >= 20]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kit.kpi("Tasks completed today", len(done_today),
                "demo data" if source.mode() == "demo" else "live", "success")
    with c2:
        kit.kpi("Study time today", f"{today_minutes/60:.1f} h",
                f"{today_minutes} min logged", "primary")
    with c3:
        kit.kpi("Active projects", len(active_projects),
                f"{len(projects)-len(active_projects)} wrapped", "primary")
    with c4:
        kit.kpi("Goals on track", f"{len(on_track)}/{len(goals)}",
                "≥20% progressed", "warning")

    st.divider()
    left, right = st.columns([3, 2])

    # --- today's checklist ---
    with left:
        st.markdown("#### ✅ Today's checklist")
        checklist = [t for t in select_for_today(tasks, 10**6)]
        if not checklist:
            kit.empty_state("No open tasks. Add one with ＋ New task.", "🎉")
        for t in checklist:
            kit.task_row(t)
            if kit.confirm_delete(t["id"], t["title"]):
                source.remove_task(t)
                st.rerun()
        st.divider()

        # weekly productivity trend (demo series in demo mode)
        st.markdown("#### 📈 Weekly productivity trend")
        if source.mode() == "demo":
            series = demo.demo_study_series(13)
            df = pd.DataFrame(series)
        else:
            df = pd.DataFrame([{"day": str(t.get("completed_at", ""))[:10],
                                "minutes": int(t.get("estimated_minutes", 0))}
                               for t in tasks_all if t.get("status") == "done"
                               and t.get("completed_at")])
            if not df.empty:
                df = (df.groupby("day", as_index=False)["minutes"].sum()
                        .sort_values("day").tail(14))
        if df.empty:
            kit.empty_state("Complete tasks to light up your trend line.", "📈")
        else:
            fig = go.Figure(go.Bar(x=df["day"], y=df["minutes"],
                                   marker_color=TOKENS["primary"]))
            fig.update_layout(height=230, margin=dict(t=10, b=0, l=10, r=10),
                              yaxis_title="min/day",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        st.caption("Study minutes per day (last 14 days)."
                   + (" Sample data — labelled demo." if source.mode() == "demo" else ""))

    with right:
        st.markdown("#### 🧠 Skills progress")
        for s in skills[:6]:
            gap = int(s.get("target_level", 5)) - int(s.get("current_level", 1))
            tone = "green" if gap <= 0 else ("blue" if gap <= 1 else "amber")
            st.markdown(
                f"**{s['name']}** "
                + kit.badge(f"L{int(s.get('current_level', 1))}", tone)
                + f" <span style='float:right;color:{TOKENS['muted']};font-size:.8rem'>"
                f"→ L{s.get('target_level', 5)}</span>",
                unsafe_allow_html=True)
            st.progress(min(s.get("current_level", 1) / max(s.get("target_level", 5), 1), 1.0))
        st.divider()
        st.markdown("#### ⏰ Upcoming deadlines")
        upcoming = [t for t in tasks if t.get("due_date")
                    and str(t["due_date"])[:10] >= tiso][:5]
        if not upcoming:
            kit.empty_state("Nothing due upcoming.", "🌤")
        for t in upcoming:
            level = deadline_notice_level(t.get("due_date"))
            kit.notice(level or "info",
                       f"{t['title']} — due {str(t['due_date'])[:10]} "
                       f"({t.get('estimated_minutes', 30)} min)")

    st.divider()
    st.markdown("#### 🤖 AI recommendation")
    _ai_daily_card(tasks, int(settings.get("daily_study_minutes", 120)))
