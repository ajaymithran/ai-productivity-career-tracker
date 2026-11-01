"""Entry point — premium shell: navy sidebar, sections, profile, app router."""
import streamlit as st

from config.settings import settings
from ui.design import inject

st.set_page_config(page_title=settings.APP_NAME, page_icon="🎯", layout="wide")
inject()

# ---------- sidebar ----------
SECTIONS = [
    ("Overview", [("Dashboard", "ui.dashboard", "📊")]),
    ("Plan", [("Daily Planner", "ui.planner", "🗓"),
              ("Projects", "ui.projects", "📁")]),
    ("Grow", [("Skills", "ui.skills", "🧠"),
              ("Career Roadmap", "ui.roadmap", "🧭")]),
    ("Assist", [("AI Coach", "ui.ai_coach", "🤖")]),
    ("Insight", [("Analytics", "ui.analytics", "📈"),
                 ("Settings", "ui.settings", "⚙️")]),
]

with st.sidebar:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:.55rem;padding:.35rem .2rem 1rem .2rem">
          <div style="width:34px;height:34px;border-radius:9px;background:#3B82F6;
               display:flex;align-items:center;justify-content:center;font-size:1.1rem">🎯</div>
          <div>
            <div style="font-weight:700;font-size:.98rem;line-height:1.1">Tracker</div>
            <div style="font-size:.68rem;opacity:.65">Productivity & Career</div>
          </div>
        </div>""",
        unsafe_allow_html=True,
    )

    nav_labels = [f"{icon} {label}" for _, items in SECTIONS for label, _, icon in items]
    route_by_label = {f"{icon} {label}": module for _, items in SECTIONS
                      for label, module, icon in items}

    choice = st.radio("Navigation", nav_labels, label_visibility="collapsed",
                      index=0)

    st.caption("")  # spacing
    # notification indicator
    try:
        import data.source as source
        n_unread = len([n for n in source.load_notifications() if not n.get("is_read")])
        st.markdown(f"<span style='font-size:.8rem;opacity:.85'>🔔 Notifications · "
                    f"{'● ' + str(n_unread) + ' unread' if n_unread else 'no unread'}</span>",
                    unsafe_allow_html=True)
    except Exception:
        pass

    st.divider()
    # profile area
    try:
        import data.source as source
        _profile = source.load_user()
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:.5rem'>"
            f"<div style='width:30px;height:30px;border-radius:50%;background:#334155;"
            f"display:flex;align-items:center;justify-content:center'>"
            f"{(_profile.get('display_name') or 'U')[0]}</div>"
            f"<div><div style='font-size:.82rem;font-weight:600'>"
            f"{_profile.get('display_name','User')}</div>"
            f"<div style='font-size:.68rem;opacity:.6'>single-user</div></div></div>",
            unsafe_allow_html=True,
        )
    except Exception:
        st.caption("👤 single-user")

    st.divider()
    # data mode badge
    try:
        import data.source as source
        live = source.mode() == "live"
        st.markdown(
            f"<span class='p-badge p-badge-{'green' if live else 'amber'}'>"
            f"{'🟢 LIVE database' if live else '🧪 DEMO data'}</span>",
            unsafe_allow_html=True,
        )
    except Exception:
        st.caption("data source unknown")

# ---------- route ----------
route = route_by_label.get(choice, "ui.dashboard")

from importlib import import_module
render = import_module(route).render
render()
