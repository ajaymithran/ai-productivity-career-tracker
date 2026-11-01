"""Diagnose Supabase sign-in problems without touching data.

Usage: ./.venv/Scripts/python.exe scripts/check_auth.py

Exit codes: 0 = sign-in OK, 1 = config problem, 2 = credentials problem.
Prints the AUTH ERROR exactly as Supabase returned it so fixes are obvious.
"""
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import settings
from supabase import create_client


def main() -> int:
    if not settings.SUPABASE_USER_EMAIL or not settings.SUPABASE_USER_PASSWORD:
        print("CONFIG PROBLEM: SUPABASE_USER_EMAIL / SUPABASE_USER_PASSWORD missing from .env")
        print("Fix: add both lines to .env (see README). They come from the user you")
        print("created in Supabase -> Authentication -> Users.")
        return 1

    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        res = client.auth.sign_in_with_password(
            {
                "email": settings.SUPABASE_USER_EMAIL,
                "password": settings.SUPABASE_USER_PASSWORD,
            }
        )
    except Exception as exc:
        print(f"CREDENTIALS PROBLEM: {type(exc).__name__}: {exc}")
        print()
        print("Common causes, in order of likelihood:")
        print("  1. '.env' password is the DASHBOARD password, not the app user's.")
        print("     (They are different accounts!)")
        print("  2. The user was never created, or the email has a typo.")
        print("  3. User exists but is not confirmed.")
        print("Fastest fix: Supabase -> Authentication -> Users -> delete the user,")
        print("then 'Add user' with the SAME email you put in .env, tick Auto-Confirm,")
        print("save the password, and update SUPABASE_USER_PASSWORD in .env to match.")
        return 2

    print(f"SIGN-IN OK as {res.user.email} (user id {res.user.id[:8]}...)")
    print("RLS will now treat queries as YOUR user - everything is green from here.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
