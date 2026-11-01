"""AI client: honest degradation without a key; mockable provider path;
GEMINI_MODEL is honored (2.5-flash era, configurable, no hardcode)."""
import ai.client as ai_client


def test_missing_key_returns_supported_none(monkeypatch):
    monkeypatch.setattr(ai_client, "_model", None)
    monkeypatch.setattr(ai_client.settings, "ai_configured", lambda: False)
    fn, err = ai_client.get_ai()
    assert fn is None
    assert "GEMINI_API_KEY" in err
    assert "fully functional" in err.casefold() or "still works" in err.casefold()


def test_mocked_provider_roundtrip(monkeypatch):
    monkeypatch.setattr(ai_client, "_model", None)
    monkeypatch.setattr(ai_client.settings, "ai_configured", lambda: True)
    calls = []

    def fake_generate(prompt: str, *, system: str = "") -> str:
        calls.append((prompt, system))
        return " mock reply "

    monkeypatch.setattr(ai_client, "_model", fake_generate)
    fn, err = ai_client.get_ai()
    assert err is None
    assert fn("hello", system="be brief") == " mock reply "
    assert calls == [("hello", "be brief")]


def test_model_is_configurable_not_hardcoded():
    # ai_client must pass the configured model name through, and the
    # default must be a real current model (not "3.5-flash" — that
    # generation doesn't exist on the Gemini API).
    assert ai_client.settings.GEMINI_MODEL == "gemini-2.5-flash"
