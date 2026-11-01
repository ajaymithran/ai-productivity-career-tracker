"""PAGE 7 — Analytics: date-range filters, trends, consistency, distribution."""
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import data.demo_data as demo
import data.source as source
from ui.components import ui_kit as kit
from ui.design import TOKENS
from src.utils.dates import today as today_local

PRIMARY = TOKENS["primary"]


def _empty(msg: str, icon: str = "📭") -> None:
    kit.empty_state(msg, icon)


def render() -> None:
    kit.page_header("📊 Analytics", "Facts from your own logged activity — nothing invented",
                    date_context=today_local().strftime("%d %b %Y"))
    kit.page_banner_demo()

    tasks_all = source.load_tasks(active_only=False)
    projects = source.load_projects()
    milestones = source.load_milestones()
    skills = source.load_skills()
    english = source.load_english_logs()

    # ---- date filter ----
    c1, c2, _ = st.columns([1.2, 1.2, 2.4])
    default_from = today_local() - timedelta(days=29)
    with c1:
        d_from = st.date_input("From", default_from, key="an_from")
    with c2:
        d_to = st.date_input("To", today_local(), key="an_to")
    if d_to < d_from:
        st.error("The end date must be on or after the start date.")
        return

    # tasks frame
    df = pd.DataFrame(tasks_all)
    if df.empty:
        _empty("No tasks have ever been logged — analytics appear as you use the Planner.",
               "🌱")
        return
    df["completed_at"] = pd.to_datetime(df.get("completed_at"), errors="coerce")
    df["done_day"] = df["completed_at"].dt.date.astype('str').replace("NaT", None)
    done = df[(df["status"] == "done") & df["completed_at"].notna()]
    done_win = done[(done["done_day"] >= str(d_from)) & (done["done_day"] <= str(d_to))]

    c3, c4, c5 = st.columns(3)
    c3.metric("Tasks completed", len(done_win), f"in {len(done_win['done_day'].unique()) if not done_win.empty else 0} day(s)")
    c4.metric("Study minutes", int(done_win["estimated_minutes"].fillna(0).sum()) if not done_win.empty else 0)
    c5.metric("Completion rate", f"{len(done) / max(len(df), 1) * 100:.0f}%",
              "all-time")

    left, right = st.columns(2)

    with left:
        st.markdown("##### ⏱ Study hours over time")
        if done_win.empty:
            _empty("Complete tasks in this window to see the study-hours line.")
        else:
            daily = done_win.groupby("done_day", as_index=False)["estimated_minutes"].sum()
            daily["day_dt"] = pd.to_datetime(daily["done_day"])
            all_days = pd.DataFrame({"day_dt": pd.date_range(d_from, d_to)})
            daily = all_days.merge(daily, on="day_dt", how="left")
            daily["estimated_minutes"] = daily.get("estimated_minutes", 0)
            if daily["estimated_minutes"].dtype.kind in "iuUO":
                daily["estimated_minutes"] = pd.to_numeric(
                    daily["estimated_minutes"], errors="coerce")
            daily["estimated_minutes"] = daily["estimated_minutes"].fillna(0.0)
            fig = go.Figure(go.Bar(x=daily["day_dt"], y=daily["estimated_minutes"],
                                   marker_color=PRIMARY))
            fig.update_layout(height=260, margin=dict(t=10), yaxis_title="min",
                              plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("##### 📉 Task completion trend")
        if done_win.empty:
            _empty("No completions in this window yet.")
        else:
            daily_c = done_win.groupby("done_day", as_index=False).size()
            all_days = pd.DataFrame({"done_day": [str(d_) for d_ in
                                                  pd.date_range(d_from, d_to)]})
            daily_c = all_days.merge(daily_c, on="done_day", how="left")
            daily_c["size"] = pd.to_numeric(daily_c["size"], errors="coerce").fillna(0).astype(int)
            fig2 = go.Figure(go.Scatter(x=daily_c["done_day"], y=daily_c["size"],
                                        mode="lines+markers",
                                        line=dict(color=TOKENS["success"])))
            fig2.update_layout(height=240, margin=dict(t=10), yaxis_title="tasks")
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("##### ⚡ Priority distribution (open work)")
        open_tasks = df[df["status"].isin(["todo", "in_progress", "backlog"])]
        if open_tasks.empty:
            _empty("No open tasks — everything is done. 🎉", "🎉")
        else:
            counts = open_tasks["priority_band"].value_counts().reindex(
                ["critical", "high", "medium", "low"]).fillna(0)
            fig3 = go.Figure(go.Pie(labels=counts.index, values=counts.values,
                                    hole=0.45,
                                    marker=dict(colors=[TOKENS["sidebar"],
                                                        TOKENS["danger"],
                                                        TOKENS["warning"], PRIMARY])))
            fig3.update_layout(height=250, margin=dict(t=10))
            st.plotly_chart(fig3, use_container_width=True)

    with right:
        st.markdown("##### 🔥 Weekly consistency")
        if source.mode() == "demo":
            series = demo.demo_study_series(days=((d_to - d_from).days // 7) * 7 or 14)
            s = pd.DataFrame(series)
            s["week"] = pd.to_datetime(s["day"]).dt.strftime("week of %d %b")
            wk = s.groupby("week", as_index=False).agg(days_active=("completed", lambda x: (x > 0).sum()),
                                                       minutes=("minutes", "sum"))
        else:
            if done_win.empty:
                wk = pd.DataFrame(columns=["week", "days_active", "minutes"])
                wk.loc[0] = ["current week", 0, 0]
            else:
                s = done_win.copy()
                s["week"] = pd.to_datetime(s["done_day"]).dt.strftime("week of %d %b")
                wk = s.groupby("week", as_index=False).agg(**{
                    "days_active": ("done_day", "nunique"),
                    "minutes": ("estimated_minutes", "sum")})
        fig4 = go.Figure(go.Bar(x=wk["week"], y=wk["days_active"],
                                marker_color=TOKENS["warning"], name="active days"))
        fig4.add_trace(go.Bar(x=wk["week"], y=wk["minutes"] / 60,
                              marker_color=PRIMARY, name="hours"))
        fig4.update_layout(barmode="group", height=260, margin=dict(t=10),
                           plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig4, use_container_width=True)

        st.markdown("##### 📁 Project progress")
        pm = []
        for p in projects:
            ms = [m for m in milestones if m.get("project_id") == p["id"]]
            done_m = sum(1 for m in ms if m.get("status") == "done")
            pm.append({"project": p["name"],
                       "progress": int(done_m / max(len(ms), 1) * 100) if ms else 0,
                       "status": p.get("status")})
        if not pm:
            _empty("No projects tracked yet.")
        else:
            pmdf = pd.DataFrame(pm)
            fig5 = go.Figure(go.Bar(y=pmdf["project"], x=pmdf["progress"],
                                    orientation="h", marker_color=PRIMARY,
                                    text=[f"{v}%" for v in pmdf["progress"]]))
            fig5.update_layout(height=200 + 30 * len(pm), margin=dict(t=10),
                               xaxis=dict(range=[0, 100]), plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig5, use_container_width=True)

        st.markdown("##### 🧠 Skill development")
        if not skills:
            _empty("No skills tracked yet.")
        else:
            kdf = pd.DataFrame([{"name": s["name"],
                                 "current": s.get("current_level", 1),
                                 "target": s.get("target_level", 5)} for s in skills])
            fig6 = go.Figure()
            fig6.add_trace(go.Bar(name="Current", y=kdf["name"], x=kdf["current"],
                                  orientation="h", marker_color=PRIMARY))
            fig6.add_trace(go.Scatter(name="Target", y=kdf["name"], x=kdf["target"],
                                      mode="markers",
                                      marker=dict(symbol="line-ew-open", size=14,
                                                  color=TOKENS["sidebar"])))
            fig6.update_layout(height=280, margin=dict(t=10), barmode="overlay",
                               plot_bgcolor="rgba(0,0,0,0)")
            fig6.update_xaxes(range=[0, 5], dtick=1)
            st.plotly_chart(fig6, use_container_width=True)

        if english:
            edf = pd.DataFrame(english)
            edf["logged_on"] = edf["logged_on"].astype(str).str[:10]
            st.markdown("##### 🗣 English minutes by type")
            efig = px.bar(edf, x="practice_type", y="minutes",
                          color="practice_type",
                          color_discrete_sequence=[PRIMARY, TOKENS["success"],
                                                   TOKENS["warning"], "#8B5CF6", "#EC4899"])
            efig.update_layout(showlegend=False, height=240, margin=dict(t=10),
                               plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(efig, use_container_width=True)