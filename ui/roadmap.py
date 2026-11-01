"""PAGE 5 — Career Roadmap: goal overview, target role, milestone timeline,
readiness categories with clear completed/active/pending distinction."""
from datetime import date, timedelta

import streamlit as st

import data.demo_data as demo
import data.source as source
from ui.components import ui_kit as kit
from ui.design import TOKENS
from src.utils.dates import today as today_local

MILESTONE_DOT = {"completed": TOKENS["success"], "active": TOKENS["primary"],
                 "pending": "#CBD5E1"}

READY_CATS = [
    ("📄 Resume status", 0.45, "resume"),
    ("🗂 Portfolio status", 0.35, "portfolio"),
    ("🎤 Interview preparation", 0.20, "interview"),
]


def _goal_overview() -> None:
    goals = source.load_goals()
    ms = source.load_career_milestones()
    with st.container():
        st.markdown("<div class='p-card'>", unsafe_allow_html=True)
        st.markdown("##### 🎯 Career goal overview")
        for g in goals:
            st.markdown(
                f"<b>{g['title']}</b> {kit.status_badge(g.get('status'))} "
                f"<span style='color:{TOKENS['muted']};font-size:.82rem'>"
                f"· {g.get('horizon','')} · due {str(g.get('target_date') or '—')[:10]}</span>",
                unsafe_allow_html=True)
            st.progress((g.get("progress_pct", 0) or 0) / 100,
                        text=f"{g.get('progress_pct', 0)}%")
        st.markdown("</div>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='p-card' style='margin-top:.7rem'>", unsafe_allow_html=True)
        st.markdown("##### 🛤 Roadmap timeline")
        for m in ms:
            dot = MILESTONE_DOT.get(m.get("status"), "#CBD5E1")
            stale = {"completed": "✅", "active": "🔵", "pending": "⚪️"}.get(m.get("status"), "⚪️")
            st.markdown(
                f"<span class='p-timeline-dot' style='background:{dot}'></span> {stale} "
                f"<b>{m['title']}</b> {kit.status_badge(m.get('status'))} "
                f"<span style='color:{TOKENS['muted']};font-size:.8rem'>{str(m.get('when'))[:10]}</span>",
                unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)


def _readiness() -> None:
    ms = source.load_career_milestones()
    completed = sum(1 for m in ms if m.get("status") == "completed")
    pct = int(completed / max(len(ms), 1) * 100)
    resume, portfolio, interview = pct + 10, max(pct - 5, 0), max(pct - 15, 0)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kit.kpi("Job readiness", f"{pct}%", "milestone-weighted", "primary")
    with c2:
        kit.kpi("📄 Resume status", f"{resume}%", "v2 drafting", "warning")
    with c3:
        kit.kpi("🗂 Portfolio status", f"{portfolio}%", "3 projects target", "primary")
    with c4:
        kit.kpi("🎤 Interview prep", f"{interview}%", "mocks pending", "danger")
    st.caption("Readiness is deterministic: completed career milestones ÷ total. "
               "Sample numbers are demo-labelled.")

    # required-skills radar input
    skills = source.load_skills()
    relevant = [s for s in skills if s.get("category") in ("Data Analytics",
                                                           "Data Science", "AI/ML")]
    with st.expander("🧩 Required skills for the target role", expanded=False):
        for s in relevant:
            kit.status_badge({"Programming": "blue"}.get(s.get("category"), "gray"))
            st.markdown(f"- **{s['name']}** — L{s.get('current_level', 1)} "
                        f"→ L{s.get('target_level', 5)} "
                        f"{'· gap' if s.get('target_level', 5) > s.get('current_level', 1) else '· ready'}")


def render() -> None:
    kit.page_header("🧭 Career Roadmap",
                    "Where you're heading and how far along you are",
                    date_context=today_local().strftime("%d %b %Y"))
    kit.page_banner_demo()

    c1, c2 = st.columns([3, 2])
    with c1:
        _goal_overview()
    with c2:
        st.markdown("<div class='p-card'>", unsafe_allow_html=True)
        st.markdown("##### 🧾 Target package")
        role = st.text_input("Target role", "Junior Data Analyst", key="tr_role")
        package = st.text_input("Target package", "3–4.5 LPA to start", key="tr_pkg")
        tdate = st.date_input("Target date", today_local() + timedelta(days=75),
                              key="tr_date")
        st.caption("These feed the AI Coach context (and stay local until DB wiring).")
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    _readiness()

    if source.mode() != "demo":
        st.info("Adding milestones across live DB lands with next wiring milestone; "
                "sample interactions above already work offline.")
    with st.form("cm_add", border=True):
        st.markdown("##### ➕ Add career milestone")
        title = st.text_input("Milestone")
        status = st.select_slider("Status", ["completed", "active", "pending"])
        when = st.date_input("When", value=None)
        if st.form_submit_button("Add milestone", type="primary") and title.strip():
            if source.mode() != "demo":
                st.info("DB wiring pending — demo flow only.")
            else:
                from data.demo_data import data as dd
                dd()["career_milestones"].append({
                    "id": f"demo-cm{len(dd()['career_milestones'])+1}",
                    "title": title.strip(), "status": status,
                    "when": when.isoformat() if when else None})
                st.toast("Added (demo)", icon="🧭")
                st.rerun()