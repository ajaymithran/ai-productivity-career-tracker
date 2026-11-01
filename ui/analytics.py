"""Analytics — study hours, completion, consistency, trends (pandas + plotly)."""
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from db import crud


@st.cache_resource
def _sup():
    from db.client import get_supabase
    return get_supabase()


def _tasks_frame(tasks: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(tasks)
    if df.empty:
        return df
    df["completed_at"] = pd.to_datetime(df.get("completed_at"), errors="coerce")
    df["due_date"] = str(df.get("due_date") or "").str[:10].replace("", None)
    df["day"] = df["completed_at"].dt.date.astype(str)
    return df


def render() -> None:
    st.header("📊 Analytics")
    st.caption("Facts only: every figure below is computed from your own rows.")

    client, err = _sup()
    if err:
        st.warning(err)
        return

    tasks = crud.list_rows(client, "tasks")
    english = crud.list_rows(client, "english_logs", order_by="logged_on", desc=True)
    df = _tasks_frame(tasks)

    if df.empty:
        st.info("No tasks yet — analytics light up as you use the Planner for a few days.")
        return

    done = df[df["status"] == "done"].dropna(subset=["completed_at"])
    done_train = done[done["day"] >= (date.today() - timedelta(days=29)).isoformat()]

    # --- Consistency streak (consecutive days with >=1 completed task) ---
    days_done = set(done_train["day"])
    streak, cursor = 0, date.today()
    while cursor.isoformat() in days_done or (streak == 0 and cursor == date.today()
                                              and not days_done):
        if cursor.isoformat() in days_done:
            streak += 1
            cursor -= timedelta(days=1)
        else:
            break

    c1, c2, c3 = st.columns(3)
    c1.metric("Tasks completed (30d)", len(done_train))
    c2.metric("Study minutes logged (30d)",
              int(done_train["estimated_minutes"].fillna(0).sum()))
    c3.metric("Current streak", f"{streak} day(s)")

    st.divider()
    left, right = st.columns(2)

    with left:
        if not done_train.empty:
            daily = done_train.groupby("day")["estimated_minutes"].sum().reset_index()
            fig = px.line(daily, x="day", y="estimated_minutes",
                          title="Study minutes per day (from completed tasks)",
                          markers=True)
            fig.update_layout(margin=dict(t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.caption("Complete tasks to build the study-minutes line.")

        band_counts = df[df["status"].isin(["todo", "in_progress"])]\
            ["priority_band"].value_counts().reindex(["high", "medium", "low"]).fillna(0)
        fig2 = px.bar(x=band_counts.index, y=band_counts.values,
                      title="Open tasks by priority band",
                      color=band_counts.index,
                      color_discrete_map={"high": "#7F1D1D", "medium": "#1E3A5F", "low": "#4A7FB5"})
        fig2.update_layout(showlegend=False, margin=dict(t=40, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    with right:
        status_counts = df["status"].value_counts()
        fig3 = px.pie(names=status_counts.index, values=status_counts.values,
                      title="All-time task status split", hole=0.45)
        fig3.update_layout(margin=dict(t=40, b=10))
        st.plotly_chart(fig3, use_container_width=True)

        if english:
            edf = pd.DataFrame(english)
            edf["logged_on"] = str(edf["logged_on"]).str[:10]
            weekly = edf[edf["logged_on"] >= (date.today() - timedelta(days=7)).isoformat()]
            fig4 = px.bar(weekly, x="practice_type", y="minutes",
                          title="English minutes by type (this week)", color="practice_type")
            fig4.update_layout(showlegend=False, margin=dict(t=40, b=10))
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.caption("Log English practice to see the weekly split.")
