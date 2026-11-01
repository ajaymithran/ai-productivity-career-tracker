"""PAGE 6 — AI Coach: chat interface, context summary, proposals with
Approve/Edit/Reject, honest offline state."""
from datetime import date

import streamlit as st

import data.demo_data as demo
import data.source as source
from ai import prompts
from ai.client import get_ai
from ui.components import ui_kit as kit
from ui.design import TOKENS
from src.utils.dates import today as today_local

GREETING = ("Hi! I'm your AI coach. I can analyse your week, surface skill gaps, "
            "or draft plans.\nEverything stays read-only; you approve anything before it counts.")


def _reply(prompt: str, context: dict) -> str:
    """Generate a reply via Gemini when available, else an honest canned coach."""
    gen, err = get_ai()
    ctx = prompts.wrap_context(context)
    if err:
        if "skills" in prompt.lower():
            gaps = context["skill_gaps"]
            if not gaps:
                return "No active skill gaps in your data — nice. I'm running in demo mode."
            big = max(gaps, key=lambda g: g["target"] - g["level"])
            return (f"Deterministic read (offline demo): biggest gap is **{big['name']}**"
                    f" at L{big['level']} vs target L{big['target']}. That's a "
                    f"{big['target'] - big['level']}-level climb; your weekly goal there is "
                    f"{big.get('min_per_week', 120)} min. Pick one exercise this week and log it.\n\n"
                    "_Live Gemini is off (no `GEMINI_API_KEY`). I still answer from your real context._")
        if "review" in prompt.lower() or not prompt.strip():
            overdue = context["overdue_tasks"]
            today = context["due_today"]
            return (f"Offline demo review:\n- Overdue: {len(overdue)}"
                    f"\n- Due today: {len(today)}"
                    f"\n- Availability: {context['availability_minutes']} min"
                    "\n\nSomething deterministic remains true: clear overdue first; "
                    "everything else is momentum.")
        return (f"(Offline demo — no Gemini key) You said: “{prompt[:120]}…”\n"
                "From your context, your most overdue focus is "
                + (context["overdue_tasks"][0]["title"] if context["overdue_tasks"]
                   else "nothing — you're clear"))
    text = gen(f"Context (authoritative JSON):\n{ctx}\n\nUser: {prompt}",
               system=prompts.SYSTEM)
    return text


def _context_summary() -> dict:
    """Deterministic facts packet for the coach (tasks, skills, goals)."""
    tasks = source.load_tasks(active_only=True)
    skills = source.load_skills()
    goals = source.load_goals()
    settings = source.load_settings()
    return prompts.build_context(
        tasks=tasks,
        skills=skills,
        goals=goals,
        availability_minutes=int(settings.get("daily_study_minutes", 120)),
    )


def render() -> None:
    kit.page_header("🤖 AI Coach", "Advice grounded in your own data — approval required always",
                    date_context=today_local().strftime("%d %b %Y"))
    kit.page_banner_demo()

    context = _context_summary()
    ctx_json = prompts.wrap_context(context)

    left, right = st.columns([3, 2])

    # ---------- chat ----------
    with left:
        if "chat" not in st.session_state:
            st.session_state["chat"] = []
        chat = st.session_state["chat"]

        with st.container(height=430):
            for msg in chat:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["text"])
            if not chat:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(GREETING)

        prompt = st.chat_input("Ask your coach anything …")
        if prompt and prompt.strip():
            chat.append({"role": "user", "text": prompt.strip()})
            with st.chat_message("user"):
                st.markdown(prompt.strip())
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Thinking over your context…"):
                    answer = _reply(prompt.strip(), context)
                st.markdown(answer)
            chat.append({"role": "assistant", "text": answer})

        q1, q2, q3 = st.columns(3)
        if q1.button("📋 Plan my day", key="qc_day", use_container_width=True):
            chat.append({"role": "user", "text": "Plan my day"})
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("…"):
                    answer = _reply("plan my day", context)
                st.markdown(answer)
            chat.append({"role": "assistant", "text": answer})
        if q2.button("🧠 Skill gap check", key="qc_gap", use_container_width=True):
            chat.append({"role": "user", "text": "Check my skill gaps"})
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("…"):
                    answer = _reply("skill gaps", context)
                st.markdown(answer)
            chat.append({"role": "assistant", "text": answer})
        if q3.button("📝 Weekly review", key="qc_rev", use_container_width=True):
            chat.append({"role": "user", "text": "Weekly review analysis"})
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("…"):
                    answer = _reply("weekly review", context)
                st.markdown(answer)
            chat.append({"role": "assistant", "text": answer})
        if chat and st.button("🧹 Clear conversation", key="qc_clear"):
            st.session_state["chat"] = []
            st.rerun()

    # ---------- context + proposals ----------
    with right:
        st.markdown("#### 🧾 Context the AI sees")
        with st.expander("Context JSON (deterministic facts)", expanded=False):
            st.code(ctx_json, language="json")

        st.markdown("#### 💡 Recommendation cards")
        for prop in source.load_proposals():
            text = (prop.get("proposal") or {}).get("text", "")
            st.markdown(f"<div class='p-card'><div style='font-weight:700;margin-bottom:.2rem'>"
                        f"📦 Proposal · {prop.get('scope')} · {prop.get('created_at','')[:10]}</div>"
                        f"<div style='font-size:.88rem;white-space:pre-wrap'>{text}</div></div>",
                        unsafe_allow_html=True)
            card_key = f"prop_{prop['id']}"[:18]
            kit.ai_card("Your decision", text, "", footer_meta="Approving records the decision; "
                        "it never edits your tasks by itself.", key=card_key)
            # persist the staged decision (Approve/Edit/Reject) via approvals service
            kit.consume_ai_decision(card_key, prop["id"])
            st.divider()

        st.markdown("#### 🗂 Approval history")
        history = source.load_decisions()
        if not history:
            kit.empty_state("No decisions yet — approve or reject a proposal above "
                            "and it will be logged here permanently.", "🗳")
        for d in history[:10]:
            tone = {"approve": "green", "reject": "red", "edit": "amber"}.get(d.get("action"), "gray")
            action_label = {"approve": "✅ Approved", "reject": "❌ Rejected",
                            "edit": "✏️ Edited"}.get(d.get("action"), d.get("action"))
            st.markdown(
                f"<div class='p-notice' style='margin:.3rem 0'>"
                f"<span class='p-badge p-badge-{tone}'>{action_label}</span> "
                f"<code style='font-size:.72rem'>{str(d.get('proposal_id'))[:8]}</code> · "
                f"<span style='font-size:.76rem;color:{TOKENS['muted']}'>"
                f"{str(d.get('decided_at'))[:16].replace('T', ' ')}</span>"
                f"{('<div style=\"font-size:.78rem;margin-top:.2rem\">📝 ' + str(d.get('notes')) + '</div>') if d.get('notes') else ''}"
                f"</div>", unsafe_allow_html=True)

        st.markdown("#### 📊 Career gap analysis (Python)")
        gaps = context["skill_gaps"]
        if not gaps:
            kit.empty_state("No active gaps — all skills at target.", "🏆")
        for g in sorted(gaps, key=lambda x: -(x["target"] - x["level"]))[:5]:
            gap_size = g["target"] - g["level"]
            kit.notice("warning" if gap_size >= 3 else "info",
                       f"**{g['name']}**: L{g['level']} → L{g['target']} "
                       f"({gap_size} level(s) to go, {g.get('min_per_week', 120)} min/wk planned)")

        from config.settings import settings as _settings
        st.caption(f"Model: {_settings.GEMINI_MODEL} when configured · "
                   f"AI is {'✅ configured' if get_ai()[1] is None else '💰 not configured — deterministic fallback in use'}")