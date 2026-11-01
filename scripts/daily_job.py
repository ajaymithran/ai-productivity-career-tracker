"""Scheduled automation that runs in GitHub Actions (never on your PC).

One thin Supabase adapter + automation.workflows.run_all() — the same
workflow code the app and tests use, so idempotency lives in ONE place
(same type+title+day notifications are never duplicated).

All notifications appear IN-APP only — never e-mail/SMS/Telegram.

Free-tier cost: seconds of runtime, a few hundred free-action minutes/year.

Required repository SECRETS (Settings → Secrets → Actions):
  SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_USER_EMAIL, SUPABASE_USER_PASSWORD
Secrets are encrypted platform-side; the service-role key stays unused.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import settings
from supabase import create_client


class SupabaseMutationStore:
    """Adapter exposing Supabase under the automation workflow protocol."""

    def __init__(self, client, user_id: str):
        self._client = client
        self._uid = user_id

    def list_tasks(self, active_only: bool = True) -> list[dict]:
        q = self._client.table("tasks").select("*")
        if active_only:
            q = q.in_("status", ["todo", "in_progress"])
        return q.execute().data or []

    def create_notification(self, notif_type: str, severity: str, title: str,
                            body: str = "", route: str = "") -> bool:
        """Idempotent: skip when an identical type+title exists for today."""
        today = date.today().isoformat()
        dup = (self._client.table("notifications").select("id")
               .eq("notif_type", notif_type).eq("title", title)
               .gte("created_at", f"{today}T00:00:00")
               .execute().data or [])
        if dup:
            return False
        self._client.table("notifications").insert({
            "user_id": self._uid, "notif_type": notif_type,
            "severity": severity, "title": title,
            "body": body or None, "route": route,
        }).execute()
        return True


def main() -> int:
    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        auth = client.auth.sign_in_with_password(
            {"email": settings.SUPABASE_USER_EMAIL,
             "password": settings.SUPABASE_USER_PASSWORD})
        # human-readable errors, never raw tracebacks in Actions logs
    except Exception as exc:
        print(f"ABORT: Supabase sign-in failed: {str(exc)[:200]}")
        return 1

    store = SupabaseMutationStore(client, auth.user.id)
    review_day = 0
    try:
        srows = client.table("user_settings").select("weekly_review_day").execute().data or []
        if srows and srows[0].get("weekly_review_day") is not None:
            review_day = int(srows[0]["weekly_review_day"])
    except Exception as exc:
        print(f"warn: could not read weekly_review_day ({str(exc)[:120]}) — using Sunday")

    from automation.workflows import run_all
    result = run_all(store, review_day=review_day)
    print(f"daily job done on {result['ran_on']}: "
          f"{result['deadline_notifications']} deadline notice(s), "
          f"{result['weekly_nudge']} weekly nudge(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
