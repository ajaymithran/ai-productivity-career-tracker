"""PAGE 2 — Daily Planner: date selector, capacity, filters, task table,
add/edit, AI schedule proposal with explicit activation, overload warnings."""
from datetime import date, timedelta

import streamlit as st

import data.source as source
from core.scheduler import select_for_today
from ui.components import ui_kit as kit
from ui.design import TOKENS


def _group(label: str, tasks: list[dict], key: str) -> None:
    st.markdown(f"##### {label} · {len(tasks)}")
    if not tasks:
        kit.empty_state("Nothing in this bucket.", "🫙")
        return
    for t in tasks:
        kit.task_row(t, key_suffix=key)
        if kit.confirm_delete(t["id"], t["title"]):
            source.remove_task(t)
            st.rerun()


def render() -> None:
    settings = source.load_settings()
    tasks = source.load_tasks(active_only=True)
    kit.page_header("🗓 Daily Planner",
                    "Plan the day, respect capacity, finish what matters",
                    primary_action=("＋ Add task", "plan_add"),
                    date_context=date.today().strftime("%d %b"))
    if kit.header_action_pressed("plan_add"):
        st.session_state["show_plan_form"] = not st.session_state.get("show_plan_form", False)
    kit.page_banner_demo()

    # date context + capacity
    plan_date = st.date_input("Planning date", date.today(),
                              help="Tasks above filter to this date; capacity from Settings.")
    availability = int(settings.get("daily_study_minutes", 120))
    st.markdown(f"""
    <div class="p-card">
      <b>Capacity today:</b> {availability} min
      &nbsp;·&nbsp; window {settings.get('study_start_time','06:30')}–{settings.get('study_end_time','22:00')}
      &nbsp;·&nbsp; <span style="color:{TOKENS['muted']}">edit in Settings</span>
    </div>""", unsafe_allow_html=True)

    if st.session_state.get("show_plan_form"):
        with st.container():
            kit.add_task_form("plan", default_due=plan_date)
        st.divider()

    # filters
    st.markdown("##### 📋 Task list")
    c1, c2, c3 = st.columns([1.2, 1.2, 2.6])
    with c1:
        f_status = st.selectbox("Status", ["all", "overdue", "due today", "no date",
                                           "upcoming"], key="pf_s")
    with c2:
        f_pri = st.multiselect("Priority", ["high", "medium", "low"],
                               default=["high", "medium", "low"], key="pf_p")
    with c3:
        f_text = st.text_input("Search", "", placeholder="filter by title…", key="pf_q")

    tiso = plan_date.isoformat()
    def match(t):
        dd = str(t.get("due_date") or "")[:10]
        if t.get("priority_band") not in f_pri:
            return False
        if f_text and f_text.lower() not in t["title"].lower():
            return False
        if f_status == "overdue":
            return dd and dd < tiso
        if f_status == "due today":
            return dd == tiso
        if f_status == "no date":
            return not dd
        if f_status == "upcoming":
            return dd and dd > tiso
        return True

    filtered = [t for t in tasks if match(t)]
    total_min = sum(int(t.get("estimated_minutes", 0)) for t in filtered)

    st.markdown(f"""
    <div style="color:{TOKENS['muted']};font-size:.85rem;margin:.2rem 0 .4rem">
      {len(filtered)} task(s) · {total_min} min scheduled
      {' · <b style="color:' + TOKENS['danger'] + '">⚠ exceeds capacity!</b>' if total_min > availability else ''}
    </div>""", unsafe_allow_html=True)
    if not filtered:
        kit.empty_state("No tasks match these filters.", "🔍")
        return

    _group("⚡ Overdue", [t for t in filtered if t.get("due_date")
                          and str(t["due_date"])[:10] < tiso], "od")
    _group("☀️ Due this date", [t for t in filtered if str(t.get("due_date") or '')[:10] == tiso], "td")
    _group("📅 Upcoming", [t for t in filtered if t.get("due_date")
                           and str(t["due_date"])[:10] > tiso], "up")
    _group("🗂 No date", [t for t in filtered if not t.get("due_date")], "nd")

    # ---- AI proposed schedule (needs explicit activation) ----
    st.divider()
    st.markdown("##### 🤖 Proposed AI schedule (pending — activate only if you approve)")
    proposal = select_for_today(filtered, availability)
    planned = sum(int(t.get("estimated_minutes", 0)) for t in proposal)
    st.markdown(
        f"<div class='p-card'><b>{len(proposal)} block(s), {planned}/{availability} min</b>"
        f"{' · <b style=\"color:' + TOKENS['danger'] + '\">overload</b>' if planned > availability else ''}"
        "<br>" + "<br>".join(
            f"⏱ {t['title']} — {t['estimated_minutes']} min" for t in proposal) +
        "</div>", unsafe_allow_html=True)
    st.caption("💡 Reason: overdue first, then priority_score greedy-fill. "
               "Nothing is scheduled until you activate.")
    c1, c2, c3 = st.columns([1, 1, 4])
    if c1.button("✅ Activate", key="plan_ap", type="primary",
                 disabled=planned > availability):
        st.session_state["active_schedule"] = [t["id"] for t in proposal]
        st.success("Activated — schedule is live for today (recorded in session).")
        st.toast("Schedule activated", icon="✅")
    if c2.button("✏️ Edit", key="plan_ed"):
        st.info("Edit a task with ✎ above, then re-propose. Actions, not autos.")
    st.session_state.setdefault("active_schedule", [])

    if st.session_state["active_schedule"]:
        with st.expander("Active schedule (click ✕ on any row to drop it)",
                         expanded=True):
            remain = availability
            for tid in st.session_state["active_schedule"]:
                t = next((x for x in filtered if x["id"] == tid), None)
                if not t:
                    continue
                cc1, cc2 = st.columns([6, .6])
                cc1.markdown(f"- **{t['title']}** · {t['estimated_minutes']} min")
                remain -= int(t["estimated_minutes"])
                if cc2.button("✕", key=f"drop_{tid}"):
                    st.session_state["active_schedule"].remove(tid)
                    st.rerun()
            st.progress(max(1 - remain / max(availability, 1), 0),
                        text=f"{availability - remain}/{availability} min used")
            if remain < 0:
                st.error(f"Over capacity by {-remain} min — unload blocks above.")
