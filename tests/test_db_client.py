"""Tests for the Supabase client factory's fail-softly + config validation."""
import pytest

from config.settings import settings
from db import client as db_client


@pytest.fixture(autouse=True)
def fake_user_creds(monkeypatch):
    """Give the client factory valid-shape user creds so the URL/key
    validation paths are what the tests actually exercise."""
    monkeypatch.setattr(settings.__class__, "SUPABASE_USER_EMAIL", "test@example.com")
    monkeypatch.setattr(settings.__class__, "SUPABASE_USER_PASSWORD", "not-a-real-password")


@pytest.fixture(autouse=True)
def clean_client():
    """Ensure no cached client leaks between tests."""
    db_client.reset_client()
    yield
    db_client.reset_client()


def test_unconfigured_gives_reason(monkeypatch):
    monkeypatch.setattr(settings.__class__, "SUPABASE_URL", "", raising=False)
    monkeypatch.setattr(settings.__class__, "SUPABASE_ANON_KEY", "", raising=False)
    c, err = db_client.get_supabase()
    assert c is None
    assert "not configured" in err


def test_key_pasted_into_url_is_caught(monkeypatch):
    """Regression: the exact error the user hit — key in the URL field."""
    monkeypatch.setattr(settings.__class__, "SUPABASE_URL", "sb_publishable_abc123")
    monkeypatch.setattr(settings.__class__, "SUPABASE_ANON_KEY", "sb_publishable_abc123")
    c, err = db_client.get_supabase()
    assert c is None
    assert "https://" in err


def test_secret_key_is_rejected(monkeypatch):
    monkeypatch.setattr(settings.__class__, "SUPABASE_URL", "https://abc.supabase.co")
    monkeypatch.setattr(settings.__class__, "SUPABASE_ANON_KEY", "sb_secret_dangerous")
    c, err = db_client.get_supabase()
    assert c is None
    assert "secret" in err and "revoke" in err


def test_dashboard_url_is_rejected(monkeypatch):
    """Regression: user pasted the browser address bar (dashboard) URL."""
    monkeypatch.setattr(
        settings.__class__, "SUPABASE_URL", "https://supabase.com/dashboard/project/xyz"
    )
    monkeypatch.setattr(settings.__class__, "SUPABASE_ANON_KEY", "sb_publishable_fine")
    c, err = db_client.get_supabase()
    assert c is None
    assert "dashboard" in err and "PROJECT URL" in err
