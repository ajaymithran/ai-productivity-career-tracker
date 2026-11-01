"""Entry point of the AI Productivity & Career Tracker.

Sidebar navigation routes to ui/<page> modules. Each page handles its own
fail-softly database banner via db.client.get_supabase().
"""
import streamlit as st

from config.settings import settings

st.set_page_config(
    page_title=settings.APP_NAME,
    page_icon="🎯",
    layout="wide",
)

# --- Theme-consistent styles (navy/blue, light neutrals) ---
st.markdown(
    """
    <style>
        .app-header {
            padding: 0.5rem 0 1rem 0;
            border-bottom: 1px solid rgba(30, 58, 95, 0.25);
            margin-bottom: 1rem;
        }
        .app-title {
            font-size: 1.6rem;
            font-weight: 700;
            color: #1E3A5F;
        }
        .app-subtitle {
            font-size: 0.95rem;
            color: rgba(60, 70, 85, 0.85);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"""
    <div class="app-header">
        <div class="app-title">🎯 {settings.APP_NAME}</div>
        <div class="app-subtitle">Your daily productivity and career command center.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- Sidebar navigation ---
NAV = {
    "Dashboard": "ui.dashboard",
    "Daily Planner": "ui.planner",
    "Projects": "ui.projects",
    "Skills": "ui.skills",
    "Career Roadmap": "ui.roadmap",
    "AI Coach": "ui.ai_coach",
    "Analytics": "ui.analytics",
    "Settings": "ui.settings",
}

with st.sidebar:
    page = st.radio("Navigation", list(NAV.keys()), label_visibility="collapsed")
    st.divider()
    st.caption("🟢 Database connected" if settings.supabase_configured()
               else "🟡 Database not configured")
    st.caption("🤖 AI on" if settings.ai_configured() else "AI off (tracker works anyway)")

from importlib import import_module

render = import_module(NAV[page]).render
render()
