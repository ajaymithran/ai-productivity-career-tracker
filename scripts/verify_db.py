"""Verify the Supabase setup end-to-end (run after Task 4 browser steps).

Expected result when everything is correct:
  * config found            -> .env has both variables
  * connection OK           -> network + credentials work
  * all 15 tables reachable -> schema.sql applied successfully
  * 0 rows returned         -> Row Level Security is ACTIVE (most important!)

RLS is why "0 rows" is a PASS: with the anon key and no user session,
every table must return an empty result. If anon could see rows, the
security model would be broken.
"""
import sys

from pathlib import Path

# Windows consoles default to cp1252, which cannot print all Unicode
# characters. Force UTF-8 with a safe fallback so explainable errors
# never crash while being explained.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.client import get_supabase
from config.settings import settings

TABLES = [
    "profiles", "user_settings", "goals", "projects", "milestones",
    "tasks", "skills", "daily_plans", "daily_plan_items", "activity_logs",
    "weekly_reviews", "english_logs", "job_readiness", "notifications",
    "ai_proposals",
]


def main() -> int:
    ok = True

    print(f"URL configured:  {bool(settings.SUPABASE_URL)}")
    print(f"Key configured:  {bool(settings.SUPABASE_ANON_KEY)}")
    if not settings.supabase_configured():
        print("FAIL: add SUPABASE_URL and SUPABASE_ANON_KEY to .env, then re-run.")
        return 1

    client, err = get_supabase()
    if err:
        print(f"FAIL: {err}")
        return 1

    leaked = []
    for table in TABLES:
        try:
            # select("*") but limited to 1 row; RLS decides if anything is visible
            res = client.table(table).select("*").limit(1).execute()
            n = len(res.data)
            if n == 0:
                print(f"PASS  {table:<18} anon sees 0 rows (RLS active)")
            else:
                # SECURITY: anon must NEVER see rows on user-owned tables
                leaked.append(table)
                print(f"LEAK  {table:<18} anon sees {n} row(s) — RLS is NOT enforced for this table!")
        except Exception as exc:
            ok = False
            msg = str(exc).split("\n")[0]
            print(f"FAIL  {table:<18} {msg[:120]}")

    print()
    if leaked:
        print("SECURITY WARNING — RLS leaks detected on:",
              ", ".join(leaked))
        print("Fix: Supabase dashboard → SQL Editor → run scripts\\show_rls_policies.sql,")
        print("then drop every policy that is not '<table>_owner_all' and re-run this check.")
        return 2
    if ok:
        print("ALL TABLES REACHABLE — RLS held.")
        return 0
    print("Some tables failed — paste the full output back to me.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
