"""Gemini client — thin wrapper with free-tier care.

Principles:
  * AI is OPTIONAL: get_ai() returns (model_fn, None) or (None, reason).
  * The app is fully functional without it (dashboards, planner, analytics).
  * Short context, single-call design: free tier ~15-60 req/day is plenty
    for one user who asks at most a few times per day.
"""
from typing import Callable

from config.settings import settings

_model: Callable | None = None


def get_ai():
    """Return (generate_fn, error_reason). Exactly one is truthy."""
    global _model

    if not settings.ai_configured():
        return None, "GEMINI_API_KEY is missing from .env — AI features are off. Everything else still works."

    if _model is not None:
        return _model, None

    try:
        from google import genai
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    except ImportError:
        return None, "google-genai package missing - run: pip install google-genai"
    except Exception as exc:
        _model = None
        return None, f"Gemini init failed: {str(exc)[:150]}"

    def generate(prompt: str, *, system: str = "") -> str:
        """One-shot text generation; raises on API errors (caller shows them)."""
        response = _client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"system_instruction": system} if system else None,
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return text

    _model = generate
    return _model, None
