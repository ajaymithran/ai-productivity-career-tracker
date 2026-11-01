"""Central configuration.

RULE: Nothing else in the app reads environment variables directly.
They import from here. One door for secrets = one place to secure.
"""
import os

from dotenv import load_dotenv

# load_dotenv() reads the .env file in the project root into os.environ.
# The .env file exists only on YOUR machine — it is never committed.
load_dotenv()


class Settings:
    """Simple container of configuration values."""

    # --- Supabase ---
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

    # --- Supabase user session (single-user app) ---
    # The app signs in as you so RLS sees an authenticated user.
    # These stay in .env (local only) — NEVER commit them.
    SUPABASE_USER_EMAIL: str = os.getenv("SUPABASE_USER_EMAIL", "")
    SUPABASE_USER_PASSWORD: str = os.getenv("SUPABASE_USER_PASSWORD", "")

    # --- Gemini ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    # Configurable provider model: override with GEMINI_MODEL in .env
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # --- App behaviour ---
    APP_NAME: str = "AI Productivity & Career Tracker"
    # Daily boundary timezone (Cloud runs UTC; the user's day is IST).
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Kolkata")

    @classmethod
    def supabase_configured(cls) -> bool:
        return bool(cls.SUPABASE_URL and cls.SUPABASE_ANON_KEY)

    @classmethod
    def ai_configured(cls) -> bool:
        return bool(cls.GEMINI_API_KEY)


settings = Settings()
