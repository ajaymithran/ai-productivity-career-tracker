"""Smoke tests for the configuration layer (Task 2).

These are deliberately simple: they verify the app's foundations import and
behave correctly. More meaningful tests (priority scoring, scheduling math)
arrive when core/ logic is written.
"""
from config.settings import Settings


def test_app_name_is_set():
    """APP_NAME must exist and be non-empty — it feeds the page title."""
    assert isinstance(Settings.APP_NAME, str)
    assert len(Settings.APP_NAME) > 0


def test_config_flags_return_booleans():
    """The 'friendly banner' logic in app.py depends on these flags
    returning bools (not None / not crashing when env vars are missing)."""
    assert isinstance(Settings.supabase_configured(), bool)
    assert isinstance(Settings.ai_configured(), bool)


def test_flags_are_false_when_env_vars_missing(monkeypatch):
    """With no env vars, both flags must be False — the fail-softly path.

    Patch the CLASS attributes (Settings), because values were captured at
    import time; patching the `settings` instance would be ignored by
    classmethods that read cls.X.
    """
    monkeypatch.setattr(Settings, "SUPABASE_URL", "", raising=False)
    monkeypatch.setattr(Settings, "SUPABASE_ANON_KEY", "", raising=False)
    monkeypatch.setattr(Settings, "GEMINI_API_KEY", "", raising=False)
    assert Settings.supabase_configured() is False
    assert Settings.ai_configured() is False


def test_settings_never_exposes_secrets_in_repr():
    """Guard against accidental secret logging via print()/log of the class."""
    s = repr(Settings)
    assert "SUPABASE_ANON_KEY" not in s or "=" not in s
