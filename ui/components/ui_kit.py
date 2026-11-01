"""Reusable UI components — every page composes these, none copy-paste them."""
import streamlit as st

from ui.design import TOKENS

MUTED = TOKENS["muted"]
NAVY = TOKENS["sidebar"]


# ---------------- page header ----------------
def page_header(title: str, subtitle: str = "", primary_action: tuple | None = None,
                notifications: int = 0, date_context: str = "") -> None:
    """primary_action = (button_label, key) rendered right of the header.
    The page itself checks for the button press after calling this."""
    c1, c2 = st.columns([4, 1.2])
    date_bit = f" · {date_context}" if date_context else ""
    c1.markdown(
        f"<div class='p-page-title'>{title}</div>"
        f"<div class='p-page-sub'>{subtitle}{date_bit}</div>",
        unsafe_allow_html=True,
    )
    if primary_action:
        c2.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
        if c2.button(primary_action[0], key=primary_action[1], type="primary",
                     use_container_width=True):
            st.session_state[f"__ph_action_{primary_action[1]}"] = True
    st.write("")


def header_action_pressed(key: str) -> bool:
    pressed = st.session_state.pop(f"__ph_action_{key}", False)
    return bool(pressed)


# ---------------- cards & badges ----------------
def kpi(label: str, value, note: str = "", accent: str = "primary") -> None:
    accent_color = {"primary": TOKENS["primary"], "success": TOKENS["success"],
                    "warning": TOKENS["warning"], "danger": TOKENS["danger"]}.get(accent, NAVY)
    st.markdown(
        f"""
        <div class="p-card" style="border-top:3px solid {accent_color};">
          <div class="p-kpi-value">{value}</div>
          <div class="p-kpi-label">{label}</div>
          <div class="p-kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi_row(*cards: tuple) -> None:
    cols = st.columns(len(cards))
    for col, (label, value, note, accent) in zip(cols, cards):
        with col:
            kpi(label, value, note, accent)


def badge(text: str, tone: str = "gray") -> str:
    return f"<span class='p-badge p-badge-{tone}'>{text}</span>"


STATUS_TONES = {"done": "green", "achieved": "green", "active": "teal",
                "in_progress": "blue", "review": "amber", "paused": "amber",
                "blocked": "red", "overdue": "red", "pending": "gray",
                "todo": "gray", "planning": "blue", "draft": "gray",
                "completed": "green", "missed": "red", "wont_do": "gray",
                "dropped": "red", "won't do": "gray"}
PRIORITY_TONES = {"high": "red", "medium": "amber", "low": "blue"}
SEV_TONES = {"urgent": "red", "warning": "amber", "info": "blue"}


def status_badge(status: str) -> str:
    return badge((status or "").replace("_", " "), STATUS_TONES.get(status, "gray"))


def priority_badge(band: str) -> str:
    return badge((band or "medium"), PRIORITY_TONES.get(band, "gray"))


def notice(severity: str, text: str) -> None:
    icon = {"urgent": "⛔", "warning": "⚠️", "info": "ℹ️"}.get(severity, "ℹ️")
    st.markdown(f"<div class='p-notice'>{icon}&nbsp; {text}</div>",
                unsafe_allow_html=True)


def page_banner_demo() -> None:
    """Shown on pages when sample data is in use."""
    from data.source import mode
    if mode() == "demo":
        st.info("🧪 **Demo data** — interactions work on sample records. "
                "Connect Supabase in `.env` for your real data.", icon="🧪")


def empty_state(message: str, icon: str = "🌱", action: tuple | None = None) -> None:
    st.markdown(
        f"""<div class='p-empty'><div style='font-size:1.5rem;margin-bottom:.3rem'>{icon}</div>{message}</div>""",
        unsafe_allow_html=True,
    )
    if action:
        c = st.columns(3)[1]
        if c.button(action[0], key=action[1], use_container_width=True):
            st.session_state[f"__es_action_{action[1]}"] = True


# ---------------- task row ----------------
def task_row(task: dict, key_suffix: str = "") -> None:
    """Compact interactive task row: badge · title · meta · ✓ · ✎ · 🗑."""
    from data import source
    overdue = False
    dd = str(task.get("due_date") or "")[:10]
    if dd:
        from datetime import date
        overdue = dd < date.today().isoformat() and task.get("status") not in ("done", "wont_do")
    color = TOKENS["danger"] if overdue else MUTED
    done = task.get("status") == "done"

    c1, c2, c3 = st.columns([0.48, 5.0, 1.7])
    with c1:
        st.markdown(f"<div style='font-weight:700;color:{NAVY};font-size:1.05rem'>"
                    f"{task.get('priority_score', 0):.1f}</div>", unsafe_allow_html=True)
    with c2:
        st.markdown(
            f"<span class='p-badge p-badge-{PRIORITY_TONES.get(task.get('priority_band'), 'gray')}'>"
            f"{(task.get('priority_band') or 'medium')}</span> "
            f"<span style=\"{'text-decoration:line-through;color:#94A3B8;' if done else ''}\">"
            f"<b>{task['title']}</b></span><br>"
            f"<span style='font-size:.76rem;color:{MUTED}'>"
            f"{task.get('estimated_minutes', 30)} min · due {dd or '—'}"
            + (f" · <b style='color:{color}'>overdue</b>" if overdue else "")
            + f" · {(task.get('notes') or '')[:60]}</span>",
            unsafe_allow_html=True,
        )
    with c3:
        b1, b2, b3 = st.columns([1, 1, 1])
        done_btn_label = "↩" if done else "✓"
        if b1.button(done_btn_label, key=f"tk_done_{task['id']}_{key_suffix}",
                     help="Complete / reopen", use_container_width=True):
            source.toggle_task_done(task)
            st.rerun()
        with b2.popover("✎", use_container_width=True):
            _task_editor(task, key_suffix)
        if b3.button("🗑", key=f"tk_del_{task['id']}_{key_suffix}",
                     help="Delete (asks confirm)", use_container_width=True):
            st.session_state[f"confirm_del_{task['id']}"] = True


def _task_editor(task: dict, key_suffix: str) -> None:
    from data import source
    from datetime import date
    title = st.text_input("Title", task["title"], key=f"et_title_{task['id']}_{key_suffix}")
    c1, c2 = st.columns(2)
    est = c1.number_input("Minutes", 5, 600, int(task.get("estimated_minutes", 30)),
                          key=f"et_est_{task['id']}_{key_suffix}")
    band = c2.select_slider("Priority", ["low", "medium", "high"],
                            task.get("priority_band", "medium"),
                            key=f"et_band_{task['id']}_{key_suffix}")
    due = st.date_input("Due date", key=f"et_due_{task['id']}_{key_suffix}",
                        value=date.fromisoformat(str(task.get("due_date"))[:10])
                        if task.get("due_date") else None)
    notes = st.text_area("Notes", task.get("notes") or "",
                         key=f"et_notes_{task['id']}_{key_suffix}")
    if st.button("Save changes", key=f"et_save_{task['id']}_{key_suffix}", type="primary"):
        if not title.strip():
            st.error("Title can't be empty")
        else:
            source.save_task_changes(task, {"title": title.strip(),
                                            "estimated_minutes": int(est),
                                            "priority_band": band,
                                            "due_date": due,
                                            "notes": notes})
            st.toast("Task updated", icon="✅")
            st.rerun()


def confirm_delete(task_id: str, label: str) -> bool:
    """Renders inline confirmation; returns True when actually delete."""
    if st.session_state.get(f"confirm_del_{task_id}"):
        c1, c2 = st.columns([3, 1])
        c1.warning(f"Delete **{label}** permanently?")
        d1, d2, _ = st.columns(3)
        if d1.button("Yes, delete", key=f"cdy_{task_id}", type="primary"):
            st.session_state.pop(f"confirm_del_{task_id}", None)
            return True
        if d2.button("Cancel", key=f"cdn_{task_id}"):
            st.session_state.pop(f"confirm_del_{task_id}", None)
            st.rerun()
    return False


# ---------------- AI recommendation card ----------------
def ai_card(title: str, body: str, reason: str = "", footer_meta: str = "",
            demo_ctx: dict | None = None, key: str = "rec") -> None:
    """AI recommendation with explicit Approve / Edit / Reject.

    Buttons only stage the decision in session state — the PAGE consumes
    it by popping f"{key}_record" and persisting via the approvals service.
    This keeps the component presentational and the audit trail in data.
    """
    st.markdown(f"""
    <div class="p-card" style="border:1px solid {TOKENS['primary']}33;">
      <div style="font-weight:700;color:{NAVY};margin-bottom:.2rem">🤖 {title}</div>
      <div style="font-size:.9rem;white-space:pre-wrap">{body}</div>
      {f"<div style='font-size:.78rem;color:{MUTED};margin-top:.4rem'>💡 <b>Why:</b> {reason}</div>" if reason else ""}
      {f"<div style='font-size:.72rem;color:{MUTED};margin-top:.3rem'>{footer_meta}</div>" if footer_meta else ""}
    </div>""", unsafe_allow_html=True)
    b1, b2, b3, _ = st.columns([1, 1, 1, 4])
    if b1.button("✅ Approve", key=f"{key}_ap", type="primary"):
        st.session_state[f"{key}_decision"] = "approve"
    if b2.button("✏️ Edit", key=f"{key}_ed"):
        st.session_state[f"{key}_decision"] = "edit"
    if b3.button("❌ Reject", key=f"{key}_rj"):
        st.session_state[f"{key}_decision"] = "reject"
    decision = st.session_state.pop(f"{key}_decision", None)
    if decision == "edit":
        with st.expander("Edit before deciding", expanded=True):
            edited = st.text_area("Adjusted advice", body, key=f"{key}_edit_ta")
            if st.button("Save edited version", key=f"{key}_edit_ok", type="primary"):
                st.session_state[f"{key}_decision"] = f"edit::{edited}"
                st.rerun()
    elif decision == "approve":
        st.session_state[f"{key}_record"] = ("approve", "")
        st.toast("Approved", icon="✅")
        st.rerun()
    elif decision == "reject":
        st.session_state[f"{key}_record"] = ("reject", "")
        st.toast("Rejected — nothing changed", icon="❌")
        st.rerun()
    elif isinstance(decision, str) and decision.startswith("edit::"):
        st.session_state[f"{key}_record"] = ("edit", decision[len("edit::"):])
        st.toast("Edited decision saved", icon="✏️")
        st.rerun()
    # feedback after the page consumes + reruns: show the durable result
    if st.session_state.get(f"{key}_record"):
        st.success("Decision recorded in your approval history. Nothing was changed silently.")


def consume_ai_decision(key: str, proposal_id: str) -> tuple | None:
    """Pop a staged decision for this card and persist it through the
    approvals service. Returns (action, notes) when something was recorded."""
    from data import source
    staged = st.session_state.pop(f"{key}_record", None)
    if not staged:
        return None
    action, notes = staged
    source.record_app_decision(proposal_id, action, notes)
    st.rerun()


# ---------------- notifications ----------------
def notifications_panel(items: list[dict]) -> None:
    """Dropdown-style panel content; caller places it in header area."""
    unread = [i for i in items if not i.get("is_read")]
    n = len(unread)
    st.markdown(f"""
    <div class="p-card" style="padding:.6rem .9rem">
      <div style="font-weight:700;color:{NAVY}">🔔 Notifications
      {badge(f"{n} unread", "red" if n else "gray")}</div>
    </div>""", unsafe_allow_html=True)
    if not items:
        st.caption("Nothing new. 🎉")
        return
    for item in items[:6]:
        sev = {"urgent": "red", "warning": "amber", "info": "blue"}.get(item.get("severity"), "gray")
        st.markdown(f"<div class='p-notice' style='margin:.25rem 0'>{badge(item.get('notif_type',''), sev)} &nbsp;{item.get('title','')}</div>",
                    unsafe_allow_html=True)


# ---------------- forms helper ----------------
def add_task_form(key_prefix: str, default_due=None) -> None:
    """Validated add-task form; calls data.source.create_task()."""
    from data import source
    with st.form(f"{key_prefix}_add", clear_on_submit=True, border=False):
        title = st.text_input("Task title", placeholder="What needs doing?",
                              key=f"{key_prefix}_t")
        c1, c2, c3 = st.columns(3)
        band = c1.select_slider("Priority", ["low", "medium", "high"], "medium",
                                key=f"{key_prefix}_b")
        impact = c2.slider("Impact", 1, 5, 3, key=f"{key_prefix}_i")
        effort = c3.slider("Effort", 1, 5, 3, key=f"{key_prefix}_e")
        c4, c5 = st.columns(2)
        est = c4.number_input("Estimated minutes", 5, 600, 30, 5, key=f"{key_prefix}_m")
        due = c5.date_input("Due date", value=default_due, key=f"{key_prefix}_d")
        if st.form_submit_button("Add task", type="primary", use_container_width=True):
            if not (title or "").strip():
                st.error("Give the task a title first.")
            else:
                source.create_task({"title": title.strip(), "priority_band": band,
                                    "impact": impact, "effort": effort,
                                    "estimated_minutes": int(est), "due_date": due,
                                    "notes": ""})
                st.toast(f"Added “{title.strip()}”", icon="✅")
