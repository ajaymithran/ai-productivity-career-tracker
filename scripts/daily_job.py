"""Scheduled automation that runs in GitHub Actions (never on your PC).

What it does (all notifications appear IN-APP only — never e-mail/SMS):
  1. urgent/warning/info notices for tasks due within 3 days (Idempotent:
     skips a notice that already exists unread with the same title+day)
  2. a weekly-review nudge on your configured review day
Free ~-tier cost: seconds of runtime, a few hundred free-action minutes/year.

Required repository SECRETS (Settings → Secrets → Actions):
  SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_USER_EMAIL, SUPABASE_USER_PASSWORD
Secrets are encrypted platform-side; the service-role key stays unused.
"""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import settings
from core.scheduler import deadline_notice_level, next_week_start
from supabase import create_client


def main() -> int:
    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    auth = client.auth.sign_in_with_password(
        {"email": settings.SUPABASE_USER_EMAIL,
         "password": settings.SUPABASE_USER_PASSWORD})
    uid = auth.user.id
    today = date.today()

    tasks = client.table("tasks").select("*")\
        .in_("status", ["todo", "in_progress"]).execute().data or []
    unread = client.table("notifications").select("*").eq("is_read", False).execute().data or []
    seen = {(n["title"], str(n["created_at"])[:10]) for n in unread}

    created = 0
    for t in tasks:
        level = deadline_notice_level(t.get("due_date"))
        if not level:
            continue
        title_map = {"urgent": "Overdue: ", "warning": "Due today: ", "info": "Upcoming: "}
        title = f"{title_map[level]}{t['title']} ({t['due_date']})"
        if (title, today.isoformat()) in seen:
            continue
        client.table("notifications").insert({
            "user_id": uid, "notif_type": "deadline", "severity": level,
            "title": title, "route": "planner",
        }).execute()
        created += 1

    # weekly review nudge on the configured day
    srows = client.table("user_settings").select("*").execute().data or [{}]
    review_day = int(srows[0].get("weekly_review_day", 0))
    if today.weekday() == (6 - review_day) % 7:  # schema: 0=Sunday..6=Saturday
        title = "Weekly review ready"
        if (title, today.isoformat()) not in seen:
            client.table("notifications").insert({
                "user_id": uid, "notif_type": "weekly_review", "severity": "info",
                "title": title,
                "body": f"Covering week starting {next_week_start(today) - timedelta(days=7)}",
                "route": "roadmap",
            }).execute()
            created += 1

    print(f"daily job done: {created} notification(s) created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
