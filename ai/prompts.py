"""Prompt construction — deterministic context in, AI suggestion out.

The context block is built by Python from real user data (never invented),
so the AI's suggestions are anchored to facts. Prompts insist the model may
only propose, never mutate. Nothing is applied without approval.
"""
import json
from datetime import date

MAX_CONTEXT_CHARS = 6000  # keep token use (and cost/quota) small


def build_context(*, tasks: list[dict], skills: list[dict], goals: list[dict],
                  availability_minutes: int, today: date | None = None) -> dict:
    """Compact factual JSON the model must reason over."""
    today = today or date.today()
    tiso = today.isoformat()
    overdue = [t for t in tasks if t.get("due_date") and str(t["due_date"])[:10] < tiso
               and t.get("status") not in ("done", "wont_do")]
    today_tasks = [t for t in tasks if t.get("due_date")
                   and str(t["due_date"])[:10] == tiso
                   and t.get("status") not in ("done", "wont_do")]
    gaps = [s for s in skills if s.get("status") == "active"
            and (s.get("target_level", 0) > s.get("current_level", 0))]
    context = {
        "today": tiso,
        "overdue_tasks": [{"title": t["title"], "due": t["due_date"],
                           "minutes": t.get("estimated_minutes")}
                          for t in sorted(overdue, key=lambda x: -x.get("priority_score", 0))][:10],
        "due_today": [{"title": t["title"], "minutes": t.get("estimated_minutes")}
                      for t in today_tasks][:10],
        "top_priority_no_due": [
            {"title": t.get("title") or t.get("name", ""), "score": t.get("priority_score", 0)}
            for t in tasks if not t.get("due_date")
            and t.get("status") not in ("done", "wont_do")][:5],
        "skill_gaps": [{"name": s["name"], "level": s.get("current_level"),
                        "target": s.get("target_level"), "min_per_week": s.get("minutes_goal_weekly")}
                       for s in gaps][:10],
        "active_goals": [{"title": g["title"], "due": g.get("target_date"),
                          "progress": g.get("progress_pct")}
                         for g in goals if g.get("status") == "active"][:5],
        "availability_minutes": availability_minutes,
    }
    return context


def wrap_context(context: dict) -> str:
    raw = json.dumps(context, indent=1, default=str)
    return raw if len(raw) <= MAX_CONTEXT_CHARS else raw[:MAX_CONTEXT_CHARS]


SYSTEM = (
    "You are a pragmatic study and career coach embedded in a personal tracker. "
    "You reason ONLY over the JSON context provided. Never invent tasks, "
    "deadlines or skills that are not in the context. Never claim you changed "
    "anything - you can only PROPOSE. Structure answers as: a one-line diagnosis, "
    "then 3-5 concrete action bullets, then one short closing note. Be specific "
    "with minutes and dates. No preamble, no disclaimers."
)

SUGGEST_TODAY = (
    "Context (authoritative JSON):\n{ctx}\n\n"
    "Ask: draft the user's plan for TODAY. Choose only from the tasks listed "
    "(overdue first), Sequence them sensibly, respect availability_minutes "
    "(never exceed it), and explain each choice in one clause. Add skill "
    "practice only if time remains. Output as numbered plan items with minutes."
)

WEEKLY_REVIEW = (
    "Context (authoritative JSON):\n{ctx}\n\n"
    "Ask: write the weekly review analysis. Group observations into "
    "consistency, overdue risk, and skill gap movement. End with 2 practical suggestions. "
    "You cannot delete anything — you may only advise."
)
