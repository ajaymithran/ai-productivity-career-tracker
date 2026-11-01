"""AI Coach — context-aware suggestions + APPROVAL workflow.

Flow: Python builds a factual context JSON -> Gemini proposes -> proposal is
stored in ai_proposals with status 'pending' -> you Approve or Reject ->
'today plan' approvals create NOTHING silently; approval of plan-type
proposals inserts the referenced tasks as *copies* with a clear origin note.

No Gemini key? Everything stays deterministic and useful.
"""
import json
from datetime import date

import streamlit as st

from ai.client import get_ai
from ai import prompts
from db import crud
from ui.components.ui_kit import empty_state


@st.cache_resource
def _sup():
    from db.client import get_supabase
    return get_supabase()


def _resolve_recs(client, uid):
    tav_entries = []
    tasks = crud.list_rows(client, "tasks", order_by="priority_score", desc=True)
    open_tasks = [t for t in tasks if t.get("status") not in ("done", "wont_do")]
    skills = crud.list_rows(client, "skills", order_by="name")
    goals = crud.list_rows(client, "goals")

    tiso = date.today().isoformat()
    for t in open_tasks:
        dd = str(t.get("due_date") or "")[:10]
        if dd and dd < tiso:
            tav_entries.append(("urgent", f"work overdue: {t['title']}", t["id"], dd))
    if not open_tasks:
        tav_entries.append(("info", "inbox zero - consider planning the week ahead", None, None))
    return open_tasks, skills, goals, tav_entries


def _fetch_proposals(client) -> list[dict]:
    return crud.list_rows(client, "ai_proposals", order_by="created_at", desc=True)


def _decide(client, uid: str, prop: dict, decision: str) -> None:
    """Record an approve/reject decision permanently. Touches no live data."""
    status = "approved" if decision == "approve" else "rejected"
    client.table("ai_proposals").update({
        "status": status,
        "applied_at": None,   # set only if a future proposal type mutates data
        "applied_result": {"note": f"decision recorded: {decision}. "
                                   "This proposal type is advisory "
                                   "(no tasks or schedules were changed)."},
    }).eq("id", prop["id"]).execute()
    from db.queries import log_activity
    log_activity(client, user_id=uid, entity_type="ai_proposal", entity_id=prop["id"],
                 action="approve" if decision == "approve" else "reject",
                 detail={"scope": prop.get("scope")})


def render() -> None:
    st.header("🤖 AI Coach")
    st.caption("Advice is anchored to YOUR data. Nothing changes without your explicit approval.")

    client, err = _sup()
    if err:
        st.warning(err)
        return
    from db import queries
    uid = queries.current_user_id(client)

    open_tasks, skills, goals, _notices = _resolve_recs(client, uid)
    stt = crud.list_rows(client, "user_settings") or [{}]
    availability = int(stt[0].get("daily_study_minutes", 120))

    context = prompts.build_context(
        tasks=open_tasks + skills, skills=skills, goals=goals,
        availability_minutes=availability,
    )

    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("🧾 Deterministic picture (Python, zero AI)")
        ctx = prompts.wrap_context(context)
        with st.expander("The exact facts the AI will see", expanded=False):
            st.code(ctx, language="json")
        import json as _json
        facts = _json.loads(ctx)
        if facts["overdue_tasks"]:
            st.error(f"{len(facts['overdue_tasks'])} overdue task(s) — triage today.")
        if facts["skill_gaps"]:
            st.info(f"{len(facts['skill_gaps'])} active skill gap(s), "
                    f"biggest: {facts['skill_gaps'][0]['name']} "
                    f"(L{facts['skill_gaps'][0]['level']} → L{facts['skill_gaps'][0]['target']}).")
        if not facts["overdue_tasks"] and not facts["skill_gaps"]:
            empty_state("Clean slate — no overdue work and no active gaps.", "🎉")

    with c2:
        st.subheader("💡 Generate AI suggestion")
        gen, gerr = get_ai()
        if gerr:
            st.info(gerr)
        q = st.radio("What should the coach consider?", ["Plan my day", "Weekly review analysis"],
                     horizontal=True)
        if st.button("Generate", type="primary", disabled=bool(gerr)):
            prompt = (prompts.SUGGEST_TODAY if q == "Plan my day" else prompts.WEEKLY_REVIEW)
            prompt = prompt.format(ctx=ctx)
            with st.spinner("Thinking…"):
                try:
                    text = gen(prompt, system=prompts.SYSTEM)
                    scope = "ai" if q == "Plan my day" else "summary"
                    client.table("ai_proposals").insert({
                        "user_id": uid, "scope": scope,
                        "prompt_context": facts, "model": "gemini-2.5-flash",
                        "proposal": {"text": text},
                        "status": "pending",
                    }).execute()
                    st.session_state["last_ai_text"] = text
                    st.success("Saved as a *pending proposal* — review below.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Gemini call failed: {str(exc)[:180]}")

    st.divider()
    st.subheader("📥 Proposals awaiting your decision")
    props = _fetch_proposals(client)
    pending = [p for p in props if p.get("status") == "pending"]
    if not pending:
        empty_state("No pending AI proposals. Generate one above, or stay offline — tracker works either way.")
    for p in pending:
        with st.container(border=True):
            text = (p.get("proposal") or {}).get("text", "")
            created = str(p.get("created_at") or "")[:16].replace("T", " ")
            st.caption(f"{p.get('scope')} · {p.get('model')} · generated {created}")
            st.markdown(text)
            b1, b2, b3 = st.columns([1, 1, 4])
            if b1.button("✅ Approve", key=f"ap_{p['id']}", type="primary"):
                _decide(client, uid, p, "approve")
                st.rerun()
            if b2.button("❌ Reject", key=f"rj_{p['id']}"):
                _decide(client, uid, p, "reject")
                st.rerun()
            st.caption("Approving records your decision in the audit trail. "
                       "The tracker never mutates tasks from AI text.")

    if len(props) > len(pending):
        with st.expander(f"🗂 Decision history ({len(props) - len(pending)} decided)"):
            for p in [x for x in props if x.get("status") != "pending"][:8]:
                st.caption(f"[{p.get('status')}] {(p.get('proposal') or {}).get('text','')[:110]}…")
