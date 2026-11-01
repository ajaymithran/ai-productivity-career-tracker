"""Shared UI kit — badges, KPI cards, empty states, notice rows.

Design language: navy #1E3A5F accents, light neutrals, WCAG-friendly sizes.
All components adapt to both themes by using Streamlit's native widgets
and translucent colour tints.
"""
import streamlit as st

NAVY = "#1E3A5F"


def kpi_card(col, label: str, value, note: str = "") -> None:
    col.markdown(
        f"""
        <div style="padding:0.9rem 1rem;border:1px solid rgba(30,58,95,0.20);
             border-radius:0.8rem;background:rgba(30,58,95,0.05);">
          <div style="font-size:0.8rem;color:rgba(60,70,85,0.75);">{label}</div>
          <div style="font-size:1.7rem;font-weight:700;color:{NAVY};">{value}</div>
          <div style="font-size:0.72rem;color:rgba(60,70,85,0.6);">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(message: str, icon: str = "🌱") -> None:
    st.markdown(
        f"""
        <div style="text-align:center;padding:1.2rem;border:1.5px dashed
             rgba(30,58,95,0.30);border-radius:0.8rem;color:rgba(60,70,85,0.8);">
          <div style="font-size:1.4rem;">{icon}</div>
          <div style="font-size:0.9rem;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


_SEV_STYLE = {
    "urgent": ("⛔", "rgba(127,29,29,0.10)"),
    "warning": ("⚠️", "rgba(154,52,18,0.10)"),
    "info": ("ℹ️", "rgba(30,58,95,0.08)"),
}


def notice_row(severity: str, text: str) -> None:
    icon, bg = _SEV_STYLE.get(severity, _SEV_STYLE["info"])
    st.markdown(
        f"<div style='padding:0.45rem 0.7rem;border-radius:0.5rem;background:{bg};"
        f"font-size:0.88rem;margin-bottom:0.3rem;'>{icon}&nbsp; {text}</div>",
        unsafe_allow_html=True,
    )


def status_badge(status: str) -> str:
    colors = {
        "active": "rgba(27,94,32,0.15)", "in_progress": "rgba(30,58,95,0.15)",
        "todo": "rgba(30,58,95,0.12)", "pending": "rgba(30,58,95,0.12)",
        "planning": "rgba(30,58,95,0.12)", "paused": "rgba(154,52,18,0.15)",
        "blocked": "rgba(127,29,29,0.18)", "overdue": "rgba(127,29,29,0.18)",
        "done": "rgba(27,94,32,0.15)", "achieved": "rgba(27,94,32,0.15)",
        "dropped": "rgba(127,29,29,0.12)", "retired": "rgba(127,29,29,0.12)",
        "abandoned": "rgba(127,29,29,0.12)", "draft": "rgba(60,70,85,0.15)",
        "missed": "rgba(127,29,29,0.15)", "wont_do": "rgba(60,70,85,0.15)",
    }
    return f"<span style='background:{colors.get(status,'rgba(60,70,85,0.12)')};padding:0.1rem 0.5rem;border-radius:0.4rem;font-size:0.78rem'>{status}</span>"
