"""Projects — milestones, deadlines, progress, blockers, GitHub links."""
from datetime import date

import streamlit as st

from db import crud
from ui.components.ui_kit import empty_state, status_badge


@st.cache_resource
def _sup():
    from db.client import get_supabase
    return get_supabase()


def _project_progress(client, project_id: str) -> tuple[int, int]:
    ms = crud.list_rows(client, "milestones", filters={"project_id": project_id},
                        order_by="position")
    done = sum(1 for m in ms if m["status"] == "done")
    return done, len(ms)


def _milestone_block(client, uid, project: dict) -> None:
    with st.expander("🧩 Milestones, blockers & notes", expanded=False):
        done, total = _project_progress(client, project["id"])
        st.progress(done / total if total else 0.0,
                    text=f"{done}/{total} milestones done")

        ms = crud.list_rows(client, "milestones", filters={"project_id": project["id"]},
                            order_by="position")
        for m in ms:
            c1, c2, c3 = st.columns([5, 2, 1.4])
            c1.markdown(f"**{m['title']}** {status_badge(m['status'])}",
                        unsafe_allow_html=True)
            if m["status"] == "blocked" and m.get("blocker"):
                c1.caption(f"⛔ {m['blocker']}")
            c2.caption(f"due {str(m.get('due_date') or '—')[:10]}")
            if c3.button("✓", key=f"ms_{m['id']}", help="Toggle done/pending"):
                new = "pending" if m["status"] == "done" else "done"
                crud.update_row(client, "milestones", m["id"], {"status": new}, user_id=uid)
                st.rerun()

        with st.form(f"addms_{project['id']}", border=False):
            title = st.text_input("New milestone", key=f"mt_{project['id']}")
            d1, d2 = st.columns(2)
            due = d1.date_input("Due (optional)", key=f"md_{project['id']}", value=None)
            pos = d2.number_input("Order", 0, 99, len(ms), key=f"mp_{project['id']}")
            blocker = st.text_input("Blocker note (optional)", key=f"mb_{project['id']}")
            if st.form_submit_button("Add milestone") and title.strip():
                stt = "blocked" if blocker.strip() else "pending"
                crud.insert_row(client, "milestones",
                                {"title": title.strip(), "project_id": project["id"],
                                 "position": int(pos),
                                 "due_date": due if due else None,
                                 "status": stt,
                                 "blocker": blocker.strip() or None}, user_id=uid)
                st.rerun()

        if project.get("notes") or project.get("blockers"):
            st.caption(f"📁 Project notes: {project.get('notes') or '—'} | "
                       f"blockers: {project.get('blockers') or '—'}")


def _project_card(client, uid: str, p: dict) -> None:
    with st.container(border=True):
        c1, c2, c3 = st.columns([4, 2, 1.6])
        c1.markdown(f"### {p['name']} &nbsp;{status_badge(p['status'])}", unsafe_allow_html=True)
        gh = p.get("github_url")
        c2.markdown(f"[GitHub repo]({gh})" if gh else "",
                    unsafe_allow_html=True) if gh else c2.caption("no repo link")
        dd = c3
        target = str(p.get("target_date") or "—")[:10]
        late = target != "—" and target < date.today().isoformat() and p["status"] not in ("done", "dropped")
        dd.markdown(f"🎯 {target}{' :red[(late)]' if late else ''}")

        if p.get("description"):
            st.caption(p["description"])

        tabs = st.tabs(["🧩 Milestones", "✍️ Edit", "🗑 Delete"])
        with tabs[0]:
            _milestone_block(client, uid, p)
        with tabs[1]:
            with st.form(f"editp_{p['id']}", border=False):
                name = st.text_input("Name", p["name"], key=f"pn_{p['id']}")
                desc = st.text_area("Description", p.get("description") or "", key=f"pd_{p['id']}")
                g1, g2 = st.columns(2)
                gh2 = g1.text_input("GitHub URL", gh or "", key=f"pg_{p['id']}")
                stat = g2.select_slider("Status", ["planning", "in_progress", "paused",
                                                   "done", "dropped"], p["status"])
                tgt = st.date_input("Target date", key=f"pt_{p['id']}",
                                    value=date.fromisoformat(target) if target != "—" else None)
                blockers = st.text_area("Blockers summary", p.get("blockers") or "", key=f"pb_{p['id']}")
                if st.form_submit_button("Save", type="primary"):
                    crud.update_row(client, "projects", p["id"],
                                    {"name": name, "description": desc,
                                     "github_url": gh2.strip() or None,
                                     "status": stat,
                                     "target_date": tgt if tgt else None,
                                     "blockers": blockers or None}, user_id=uid)
                    st.rerun()
        with tabs[2]:
            st.write("Deleting a project **cascades** to its milestones. Tasks keep but lose the link.")
            if st.button("Delete project", key=f"delp_{p['id']}"):
                crud.delete_row(client, "projects", p["id"], user_id=uid, label=p["name"])
                st.rerun()


def render() -> None:
    st.header("📁 Projects")
    st.caption("Ship work publicly: milestones track progress, blockers stay visible.")

    client, err = _sup()
    if err:
        st.warning(err)
        return
    from db import queries
    uid = queries.current_user_id(client)

    with st.form("addproj", border=True, clear_on_submit=True):
        st.subheader("➕ New project")
        name = st.text_input("Name", placeholder="e.g. Portfolio dashboard app")
        desc = st.text_area("Short description")
        c1, c2 = st.columns(2)
        gh = c1.text_input("GitHub URL (optional)", placeholder="https://github.com/...")
        tgt = c2.date_input("Target date (optional)", value=None)
        if st.form_submit_button("Create project", type="primary") and name.strip():
            crud.insert_row(client, "projects",
                            {"name": name.strip(), "description": desc.strip() or None,
                             "github_url": gh.strip() or None,
                             "start_date": date.today(),
                             "target_date": tgt},
                            user_id=uid)
            st.rerun()

    st.divider()
    projects = crud.list_rows(client, "projects", order_by="start_date", desc=False)
    if not projects:
        empty_state("No projects yet. Every career-worthy app starts as a blank form.", "📁")
    for p in projects:
        _project_card(client, uid, p)
