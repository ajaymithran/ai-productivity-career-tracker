"""Skills — level tracking, gap analysis, English logs."""
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from db import crud
from ui.components.ui_kit import empty_state, status_badge


@st.cache_resource
def _sup():
    from db.client import get_supabase
    return get_supabase()


DEFAULT_SKILLS = [
    ("Python", "technical"), ("SQL", "analytics"), ("Excel", "analytics"),
    ("Power BI", "analytics"), ("Statistics", "analytics"),
    ("Machine Learning", "ai"), ("AI tools", "ai"), ("English", "language"),
]


def _gap_chart(skills: list[dict]) -> None:
    df = pd.DataFrame(skills)
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Current", x=df["name"], y=df["current_level"],
                         marker_color="#4A7FB5"))
    fig.add_trace(go.Bar(name="Target", x=df["name"], y=df["target_level"],
                         marker_color="#1E3A5F"))
    fig.update_layout(barmode="group", height=340,
                      margin=dict(t=30, b=10, l=10, r=10),
                      yaxis=dict(range=[0, 5], tick0=1, dtick=1),
                      title="Skill gap analysis (levels 1-5)")
    st.plotly_chart(fig, use_container_width=True)


def render() -> None:
    st.header("🧠 Skills")
    st.caption("Your 8 core skills and anything else. Levels: 1=beginner … 5=strong.")

    client, err = _sup()
    if err:
        st.warning(err)
        return
    from db import queries
    uid = queries.current_user_id(client)

    with st.form("addskill", border=True, clear_on_submit=True):
        st.subheader("➕ New skill")
        c1, c2, c3 = st.columns([2, 1, 1])
        name = c1.text_input("Name", placeholder="Python, SQL, Excel, Power BI…")
        cat = c2.selectbox("Category", ["technical", "analytics", "ai", "language", "soft"])
        weekly = c3.number_input("Weekly minutes goal", 15, 3000, 180, 15)
        if st.form_submit_button("Add skill") and name.strip():
            crud.insert_row(client, "skills",
                            {"name": name.strip(), "category": cat,
                             "current_level": 1, "target_level": 5,
                             "minutes_goal_weekly": int(weekly)}, user_id=uid)
            st.rerun()

    st.divider()
    skills = crud.list_rows(client, "skills", order_by="name")
    if not skills:
        empty_state("No skills yet — start with Python, SQL, Excel, Power BI, Statistics, ML, AI tools and English.", "🧠")
        return

    left, right = st.columns([3, 2])
    with left:
        active = [s for s in skills if s.get("status") == "active"]
        if active:
            gdf = [s for s in active if s.get("target_level", 0) > s.get("current_level", 0)]
            if gdf:
                _gap_chart(gdf)
        for s in skills:
            with st.container(border=True):
                c1, c2 = st.columns([3, 2])
                c1.markdown(f"### {s['name']} {status_badge(s['status'])} *{s['category']}*",
                            unsafe_allow_html=True)
                c2.caption(f"goal: {s.get('minutes_goal_weekly',180)} min/week")
                lvl = c2.number_input("Current level", 1, 5, s.get("current_level", 1),
                                      key=f"lvl_{s['id']}")
                tgt = c2.number_input("Target level", 1, 5, s.get("target_level", 5),
                                      key=f"tgt_{s['id']}")
                b1, b2, b3 = st.columns(3)
                if (int(lvl) != s.get("current_level") or int(tgt) != s.get("target_level")):
                    if b1.button("Save levels", key=f"sv_{s['id']}", type="primary"):
                        if tgt and int(tgt) < int(lvl):
                            st.error("Target must be >= current level")
                        else:
                            crud.update_row(client, "skills", s["id"],
                                            {"current_level": int(lvl),
                                             "target_level": int(tgt)}, user_id=uid)
                            st.rerun()
                if b2.selectbox(" ", ["", "pause", "retire", "reactivate"], key=f"act_{s['id']}",
                                format_func=lambda x: x or "action…"):
                    action = st.session_state[f"act_{s['id']}"]
                    stt = {"pause": "paused", "retire": "retired", "reactivate": "active"}[action]
                    crud.update_row(client, "skills", s["id"], {"status": stt}, user_id=uid)
                    st.rerun()
                if b3.button("🗑", key=f"del_{s['id']}"):
                    crud.delete_row(client, "skills", s["id"], user_id=uid, label=s["name"])
                    st.rerun()

    with right:
        st.markdown("###### 🗣 English practice log")
        en_skill = next((s for s in skills if s["name"].lower() == "english"), None)
        with st.form("englog", border=True):
            pt = st.select_slider("Practice type", ["speaking", "listening", "reading",
                                                    "writing", "vocabulary"])
            mins = st.number_input("Minutes", 1, 300, 30)
            conf = st.slider("Confidence today", 1, 5, 3,
                             help="1=low, 5=near-native feel")
            note = st.text_input("Note (optional)")
            if st.form_submit_button("Log practice") and en_skill:
                crud.insert_row(client, "english_logs",
                                {"skill_id": en_skill["id"], "practice_type": pt,
                                 "minutes": int(mins), "confidence": conf,
                                 "logged_on": date.today(), "notes": note or None},
                                user_id=uid)
                st.rerun()
            if not en_skill:
                st.caption("Add a skill named 'English' to unlock logging.")
        logs = crud.list_rows(client, "english_logs", order_by="logged_on", desc=True) if en_skill else []
        if logs:
            df = pd.DataFrame(logs)
            df["logged_on"] = str(df["logged_on"])
            week = df[df["logged_on"] >= (date.today() - timedelta(days=7)).isoformat()]
            st.metric("Minutes this week", int(week["minutes"].sum()) if len(week) else 0)
            st.dataframe(
                df[["logged_on", "practice_type", "minutes", "confidence", "notes"]]
                .head(10).style.format({"minutes": "{}"}),
                use_container_width=True, hide_index=True,
            )
