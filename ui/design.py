"""Design system — tokens + one global CSS injection.

Palette (Linear/Notion-inspired):
  sidebar #111827 · bg #F8FAFC · card #FFFFFF · primary #3B82F6
  success #14B8A6 · warning #F59E0B · danger #EF4444
  text #111827 · muted #64748B · border #E2E8F0
"""
import streamlit as st

TOKENS = {
    "sidebar": "#111827", "bg": "#F8FAFC", "card": "#FFFFFF",
    "primary": "#3B82F6", "success": "#14B8A6", "warning": "#F59E0B",
    "danger": "#EF4444", "text": "#111827", "muted": "#64748B",
    "border": "#E2E8F0", "radius": "14px",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {
  --navy:#111827; --bg:#F8FAFC; --card:#FFFFFF; --primary:#3B82F6;
  --success:#14B8A6; --warning:#F59E0B; --danger:#EF4444;
  --text:#111827; --muted:#64748B; --border:#E2E8F0; --radius:14px;
}

html, body, [class*="css"], .stApp, .stMarkdown, .stButton button,
.stTextInput input, .stNumberInput input, .stDateInput input,
.stTimeInput input, .stSelectbox div[data-baseweb="select"] > div {
  font-family: 'Inter', -apple-system, 'Segoe UI', system-ui, sans-serif !important;
  color: var(--text);
}

/* main area shell */
.block-container { max-width: 1180px; padding: 1.6rem 2rem 3.2rem; }
.stApp { background: var(--bg); }

/* dark navy sidebar */
[data-testid="stSidebar"] {
  background: var(--navy);
  color: #F1F5F9;
}
[data-testid="stSidebar"] * { color: #E2E8F0; }
[data-testid="stSidebar"] hr { border-color: rgba(226,232,240,0.15); }
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
  font-size: 0.9rem;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label {
  padding: 0.3rem 0.55rem; border-radius: 8px;
}
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label:hover {
  background: rgba(59,130,246,0.15);
}

/* cards */
.p-card {
  background: var(--card); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 1rem 1.15rem;
  box-shadow: 0 1px 2px rgba(17,24,39,0.04), 0 4px 12px rgba(17,24,39,0.03);
}
.p-kpi-value { font-size: 1.85rem; font-weight: 700; color: var(--navy); line-height: 1.15; }
.p-kpi-label { font-size: 0.8rem; color: var(--muted); font-weight: 500; }
.p-kpi-note  { font-size: 0.72rem; color: var(--muted); }

/* page header + actions */
.p-page-title { font-size: 1.55rem; font-weight: 700; color: var(--navy); }
.p-page-sub   { font-size: 0.9rem; color: var(--muted); }

/* badges */
.p-badge {
  display:inline-block; padding:0.12rem 0.6rem; border-radius:999px;
  font-size:0.72rem; font-weight:600; letter-spacing:0.01em;
  border:1px solid transparent;
}
.p-badge-green  { background:#ECFDF5; color:#065F46; border-color:#A7F3D0; }
.p-badge-blue   { background:#EFF6FF; color:#1D4ED8; border-color:#BFDBFE; }
.p-badge-amber  { background:#FFFBEB; color:#92400E; border-color:#FDE68A; }
.p-badge-red    { background:#FEF2F2; color:#991B1B; border-color:#FECACA; }
.p-badge-gray   { background:#F1F5F9; color:#475569; border-color:#E2E8F0; }
.p-badge-teal   { background:#F0FDFA; color:#0F766E; border-color:#99F6E4; }

/* notice stripe */
.p-notice {
  padding:0.5rem 0.8rem; border-radius:10px; font-size:0.87rem;
  border:1px solid var(--border); background:var(--card); color:var(--text);
}

/* empty state */
.p-empty {
  text-align:center; padding:1.6rem 1rem; color:var(--muted);
  border:1.5px dashed #CBD5E1; border-radius:var(--radius); font-size:0.9rem;
  background:rgba(248,250,252,0.6);
}

/* buttons */
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {
  background: var(--primary); border-color: var(--primary);
}
.stButton > button { border-radius: 10px; font-weight: 600; }

/* kanban */
.p-kanban-col {
  background:#F1F5F9; border:1px solid var(--border);
  border-radius:var(--radius); padding:0.7rem; min-height:120px;
}

/* chat */
[data-testid="stChatMessage"] { background: var(--card); border:1px solid var(--border);
  border-radius: var(--radius); }

/* timeline */
.p-timeline-dot { height:10px; width:10px; border-radius:50%; display:inline-block; }

@media (max-width: 780px) {
  .block-container { padding: 1rem 0.8rem 2.4rem; }
  .p-kpi-value { font-size: 1.5rem; }
}
</style>
"""


def inject() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
