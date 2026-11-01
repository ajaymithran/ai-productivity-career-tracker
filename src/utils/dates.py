"""Timezone-aware "today" — the single daily-boundary the app uses.

Why: Streamlit Community Cloud runs on UTC; the user's day (IST) can start
while the server still says "yesterday", flipping "due today" behaviour at
deployment. Every UI page calls today() instead of date.today().
Overridable with TIMEZONE in .env (any IANA name); degrades to local time.
"""
from datetime import date, datetime

from config.settings import settings


def today() -> date:
    tz_name = getattr(settings, "TIMEZONE", "") or "Asia/Kolkata"
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        # unknown tz name / tzdata missing: honest fallback to host-local time
        return datetime.now().date()
