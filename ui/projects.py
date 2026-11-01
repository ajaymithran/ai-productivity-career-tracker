"""PAGE 3 — Projects: overview cards, Kanban, detail with milestone timeline."""
from datetime import date

import streamlit as st

import data.source as source
from ui.components import ui_kit as kit
from ui.design import TOKENS
from src.utils.dates import today as today_local

KANBAN_COLS = ["pending", "in_progress", "review", "done"]
KANBAN_LABEL = {"pending": "📋 To Do", "in_progress": "🚧 In Progress",
                "review": "🔍 Review", "done": "✅ Completed"}


def _progress(p: dict, milestones: list[dict]) -> tuple[int, int]:
    ms = [m for m in milestones if m.get("project_id") == p["id"]]
    return sum(1 for m in ms if m.get("status") == "done"), len(ms)


def _detail_expander(p: dict, ms: list[dict]) -> None:
    with st.expander("🧭 Project detail — milestone timeline", expanded=False):
        ms = sorted(ms, key=lambda m: (m.get("position", 0), m.get("due_date") or ""))
        if not ms:
            kit.empty_state("No milestones yet — add one below.", "🧩")
        for m in ms:
            dot = {"done": TOKENS["success"], "in_progress": TOKENS["primary"],
                   "blocked": TOKENS["danger"]}.get(m.get("status"), "#94A3B8")
            st.markdown(
                f"<span class='p-timeline-dot' style='background:{dot};margin-right:.5rem'></span>"
                f"<b>{m['title']}</b> {kit.status_badge(m.get('status'))} "
                f"<span style='color:{TOKENS['muted']};font-size:.8rem'>due "
                f"{str(m.get('due_date') or '—')[:10]}"
                + (f" · ⛔ {m['blocker']}" if m.get('blocker') and m['status'] == 'blocked' else "")
                + "</span>", unsafe_allow_html=True)
        with st.form(f"msadd_{p['id']}", border=False):
            title = st.text_input("New milestone", key=f"mst_{p['id']}")
            c1, c2 = st.columns(2)
            due = c1.date_input("Due", key=f"msd_{p['id']}", value=None)
            blocker = c2.text_input("Blocker (optional)", key=f"msb_{p['id']}")
            if st.form_submit_button("Add milestone") and title.strip():
                if source.mode() != "demo":
                    st.info("Milestone creation lands with DB wiring — demo only shows the flow.")
                else:
                    from data.demo_data import data as dd
                    dd()["milestones"].append({
                        "id": f"demo-m{len(dd()['milestones'])+1}",
                        "project_id": p["id"], "title": title.strip(),
                        "position": len(ms) + 1,
                        "due_date": due.isoformat() if due else None,
                        "status": "blocked" if blocker.strip() else "pending",
                        "blocker": blocker.strip() or None, "user_id": "demo"})
                    st.toast("Milestone added (demo)", icon="🧩")
                    st.rerun()


def _project_card(p: dict, milestones: list[dict]) -> None:
    with st.container():
        st.markdown(f"""
        <div class="p-card">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <b style="color:{TOKENS['navy'] if 'navy' in TOKENS else TOKENS['sidebar']}">{p['name']}</b>
            <span>{kit.status_badge(p['status'])}</span>
          </div>
          <div style="color:{TOKENS['muted']};font-size:.85rem;margin:.2rem 0 .5rem">
            {p.get('description') or ''}
          </div>
        </div>""", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([2, 1.4, 1.4])
        done, total = _progress(p, milestones)
        c1.progress(done / total if total else 0.0,
                    text=f"{done}/{total} milestones")
        c2.caption(f"🎯 {str(p.get('target_date') or '—')[:10]}")
        gh = p.get("github_url")
        (c3.markdown(f"[🔗 GitHub]({gh})") if gh else c3.caption("no repo link"))
        if p.get("blockers"):
            kit.notice("warning", f"Blocker: {p['blockers']}")
        d1, d2, _ = st.columns([1, 1, 4])
        d1.button("✎ Edit", key=f"pe_{p['id']}")
        d2.button("🗑", key=f"pd_{p['id']}")
        _detail_expander(p, milestones)
        st.write("")


def render() -> None:
    projects = source.load_projects()
    milestones = source.load_milestones()
    tasks = source.load_tasks(active_only=False)
    kit.page_header("📁 Projects", "Milestones, deadlines, blockers — one board per project",
                    date_context=f"{len(projects)} projects")
    kit.page_banner_demo()

    view = st.segmented_control("View", ["Cards", "Kanban"], default="Cards",
                                label_visibility="collapsed") or "Cards"

    if view == "Cards":
        for p in projects:
            _project_card(p, milestones)
    else:
        cols = st.columns(4)
        for col, status in zip(cols, KANBAN_COLS):
            with col:
                st.markdown(
                    f"<div class='p-kanban-col-header' style='font-weight:700;margin-bottom:.3rem'>{KANBAN_LABEL[status]} · "
                    f"{sum(1 for p in projects if p.get('status') == status)}</div>",
                    unsafe_allow_html=True)
                for p in [x for x in projects if x.get("status") == status]:
                    done_m, total_m = _progress(p, milestones)
                    target = str(p.get("target_date") or "—")[:10]
                    late = target not in ("—",) and target < today_local().isoformat() \
                        and status not in ("done", "review")
                    st.markdown(f"""
                      <div class="p-card" style="padding:.65rem .8rem;margin-bottom:.5rem">
                        <b style="font-size:.9rem">{p['name']}</b><br>
                        <span style="font-size:.75rem;color:{TOKENS['muted']}">
                        {done_m}/{total_m} milestones · 🎯 {target}
                        {' · ⛔' if late else ''}</span>
                      </div>""", unsafe_allow_html=True)
                    with st.popover("⋯", use_container_width=True, key=f"kb_{p['id']}"):
                        _detail_expander(p, milestones)

    # add project
    st.divider()
    with st.form("proj_add", border=True):
        st.markdown("##### ➕ Add project")
        name = st.text_input("Name", placeholder="e.g. Portfolio site v2")
        desc = st.text_area("Description", height=60)
        c1, c2 = st.columns(2)
        gh = c1.text_input("GitHub URL", placeholder="https://github.com/…")
        tgt = c2.date_input("Target date", value=None)
        if st.form_submit_button("Create project", type="primary") and name.strip():
            if source.mode() != "demo":
                st.info("DB-backed creation is wired via db/queries for tasks; "
                        "project CRUD hooks to live tables next milestone.")
            else:
                from data.demo_data import data as dd
                dd()["projects"].append({
                    "id": f"demo-p{len(dd()['projects'])+1}", "user_id": "demo",
                    "name": name.strip(), "description": desc.strip() or None,
                    "github_url": gh.strip() or None,
                    "start_date": today_local().isoformat(),
                    "target_date": tgt.isoformat() if tgt else None,
                    "status": "pending", "blockers": None, "notes": ""})
                st.toast("Project created (demo)", icon="📁")
                st.rerun()