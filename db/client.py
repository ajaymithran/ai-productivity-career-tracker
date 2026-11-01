"""Supabase client factory.

Design rules:
  * Nothing else in the app talks to supabase-py directly — they call
    get_supabase() here. One door for the DB, like settings.py for secrets.
  * Lazy creation + user sign-in: the client authenticates with YOUR user
    credentials so every query carries your session and RLS can enforce
    row ownership. Without a session, RLS returns nothing (see verify_db).
  * Fail softly: returns (client, None) on success or (None, reason) on
    failure, so UI code can show a friendly banner instead of crashing.
"""
import sys

from supabase import Client, create_client

from config.settings import settings

_client: Client | None = None
_last_error: str | None = None


def _validate_config() -> str | None:
    """Check value *shapes* before any network call.

    Catches the classic copy-paste mistakes (key pasted into the URL field,
    dashboard URL pasted as project URL, secret key pasted as anon key)
    with a message a human can act on.
    """
    url, key = settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY

    if not url.startswith(("http://", "https://")):
        return (
            "SUPABASE_URL must start with https:// (the Project URL from "
            f"Settings -> API). It currently starts with: '{url[:20]}'. "
            "Common cause: the publishable key was pasted into the URL field."
        )
    if "supabase.com/dashboard" in url:
        return (
            "SUPABASE_URL contains the DASHBOARD URL (supabase.com/dashboard). "
            "Copy the PROJECT URL instead: it looks like "
            "'https://<projectref>.supabase.co' and sits right above the API "
            "keys on the API Keys page."
        )
    if key.startswith("sb_secret") or key.startswith("sb_secret_"):
        return (
            "SUPABASE_ANON_KEY contains a SECRET key (sb_secret_), which bypasses "
            "row-level security and must never be used by this app. Use the "
            "PUBLISHABLE key (sb_publishable_) or the legacy anon JWT instead, "
            "and revoke the secret key in Supabase -> Settings -> API."
        )
    publishable_ok = key.startswith("sb_publishable") or key.startswith("eyJ")
    if not publishable_ok:
        return (
            "SUPABASE_ANON_KEY doesn't look like a publishable key (sb_publishable_) "
            "or a legacy anon JWT (eyJ...). Check Settings -> API -> Publishable key."
        )
    return None


def get_supabase():
    """Return (client, error_reason). Exactly one is truthy."""
    global _client, _last_error

    if not settings.supabase_configured():
        return None, "Supabase is not configured. Add SUPABASE_URL and SUPABASE_ANON_KEY to your .env file."

    # Shape validation FIRST — it produces the most actionable diagnosis.
    shape_error = _validate_config()
    if shape_error:
        _last_error = shape_error
        return None, shape_error

    if not (settings.SUPABASE_USER_EMAIL and settings.SUPABASE_USER_PASSWORD):
        _reason = (
            "Supabase USER login missing. Add SUPABASE_USER_EMAIL and "
            "SUPABASE_USER_PASSWORD to .env (the single user you created in "
            "Task 4). The app signs in as you so RLS can identify your rows."
        )
        _last_error = _reason
        return None, _reason

    if _client is not None:
        return _client, None

    try:
        # The ANON key identifies the Supabase *project machine*, the user
        # credentials identify YOU. Together they let RLS do its job.
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        auth_res = client.auth.sign_in_with_password(
            {
                "email": settings.SUPABASE_USER_EMAIL,
                "password": settings.SUPABASE_USER_PASSWORD,
            }
        )
        if auth_res is None or auth_res.user is None:
            raise RuntimeError("Sign-in returned no user - check email/password in .env")
    except Exception as exc:  # pragma: no cover - network/environment specific
        _last_error = f"Supabase sign-in failed: {exc}".split("\n")[0]
        return None, _last_error

    _client = client
    _last_error = None
    return _client, None


def reset_client() -> None:
    """Forget the cached client (used after .env edits / in tests)."""
    global _client
    _client = None
    _last_error = None
