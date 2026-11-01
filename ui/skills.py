"""PAGE 4 — Skills: categories, levels, gap analysis, last practiced."""
from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import data.source as source
from ui.components import ui_kit as kit
from ui.design import TOKENS

CATEGORIES = ["Programming", "Data Analytics", "Data Science", "AI/ML", "Communication"]
CAT_EMOJI = {"Programming": "🐍", "Data Analytics": "📊", "Data Science": "📐",
             "AI/ML": "🤖", "Communication": "🗣"}


def _gap_chart(skills: list[dict]) -> None:
    gapped = [s for s in skills if int(s.get("target_level", 5)) > int(s.get("current_level", 1))]
    if not gapped:
        kit.empty_state("No gaps left — you're at target on everything tracked. 🏆", "🎓")
        return
    ago = sorted(gapped, key=lambda s: (-int(s.get("target_level", 5))
                                        + int(s.get("current_level", 1))))
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Current", y=[s["name"] for s in ago],
                         x=[s.get("current_level", 1) for s in ago],
                         orientation="h", marker_color=TOKENS["primary"]))
    fig.add_trace(go.Scatter(name="Target", y=[s["name"] for s in ago],
                             x=[s.get("target_level", 5) for s in ago],
                             mode="markers", marker=dict(symbol="line-ew-open",
                                                         size=16, color=TOKENS["sidebar"])))
    fig.update_layout(title="Skill gap (bars = current, ticks = target)",
                      height=300 + 24 * len(ago), barmode="overlay",
                      xaxis=dict(range=[0, 5], dtick=1),
                      margin=dict(t=40, b=10, l=10, r=10),
                      plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)


def _skill_card(s: dict) -> None:
    gap = int(s.get("target_level", 5)) - int(s.get("current_level", 1))
    tone = "green" if gap <= 0 else ("blue" if gap <= 1 else "amber")
    lp = str(s.get("last_practiced") or "—")[:10]
    st.markdown(f"""
    <div class="p-card">
      <div style="display:flex;justify-content:space-between">
        <b>{s['name']}</b> {kit.badge(s.get('category',''), 'blue')}
        <span>{kit.badge(f"L{int(s.get('current_level',1))} → L{int(s.get('target_level',5))}", tone)}</span>
      </div>
      <div style="font-size:.78rem;color:{TOKENS['muted']};margin:.25rem 0">
        last practiced {lp}{f" · {', '.join(n for n in (s.get('linked_projects') or []))}" if s.get('linked_projects') else ""} ·
        goal {s.get('minutes_goal_weekly',180)} min/wk
      </div>
    </div>""", unsafe_allow_html=True)
    st.progress(min(s.get("current_level", 1) / max(s.get("target_level", 5), 1), 1.0))


def render() -> None:
    skills = source.load_skills()
    kit.page_header("🧠 Skills", "Five categories, honest levels, visible gaps",
                    date_context=f"{len(skills)} skills tracked")
    kit.page_banner_demo()

    tabs = st.tabs([f"{CAT_EMOJI[c]} {c}" for c in CATEGORIES if c] +
                   ["📈 Gap view"])
    cat_tabs = tabs[:-1]
    any_skill = False
    for tab, cat in zip(cat_tabs, CATEGORIES):
        with tab:
            items = [s for s in skills if s.get("category") == cat]
            if not items:
                kit.empty_state(f"No {cat} skills tracked yet — add one below.", CAT_EMOJI[cat])
                continue
            any_skill = True
            c1, c2 = st.columns(2)
            eng_engish = [s for s in items if s["name"].lower() == "english"]
            for i, s in enumerate(items):
                with (c1 if i % 2 == 0 else c2):
                    _skill_card(s)
                    cc1, cc2 = st.columns(2)
                    new_level = cc1.slider("Current", 1, 5, int(s.get("current_level", 1)),
                                           key=f"sl_{s['id']}")
                    new_target = cc2.slider("Target", 1, 5, int(s.get("target_level", 5)),
                                            key=f"st_{s['id']}")
                    save = st.button("Save levels",
                                     key=f"ss_{s['id']}",
                                     type="primary"
                                     if new_level != s.get("current_level")
                                     and new_target >= new_level else "secondary")
                    if save:
                        if new_target < new_level:
                            st.error("Target must be ≥ current level.")
                        else:
                            if source.mode() != "demo":
                                st.info("Live save lands with DB wiring (existing live "
                                        "updates already work on the DB pages).")
                            else:
                                from data.demo_data import data as dd
                                for item in dd()["skills"]:
                                    if item["id"] == s["id"]:
                                        item["current_level"] = new_level
                                        item["target_level"] = new_target
                                st.toast(f"{s['name']} updated (demo)", icon="🧠")
                                st.rerun()

    with tabs[-1]:
        _gap_chart([s for s in skills if s.get("status") == "active"])

    st.divider()
    with st.form("skill_add", border=True):
        st.markdown("##### ➕ Add skill")
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Name")
        cat = c2.selectbox("Category", CATEGORIES)
        goal = c3.number_input("Weekly minutes goal", 15, 3000, 120, 15)
        if st.form_submit_button("Add skill", type="primary") and name.strip():
            if source.mode() != "demo":
                st.info("Hooking to live DB next milestone.")
            else:
                from data.demo_data import data as dd
                dd()["skills"].append({
                    "id": f"demo-s{len(dd()['skills'])+1}", "user_id": "demo",
                    "name": name.strip(), "category": cat, "current_level": 1,
                    "target_level": 5, "minutes_goal_weekly": int(goal),
                    "status": "active", "last_practiced": None, "linked_projects": []})
                st.toast("Skill added (demo)", icon="🧠")
                st.rerun()
