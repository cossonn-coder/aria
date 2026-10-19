# tests/llm/test_groq_413.py
#
# Sprint 25 / dette #73 : un 413 Groq saute les autres entrées groq* de la
# requête et passe directement à DeepSeek, sans cache négatif.

import httpx
import pytest

from llm.llm_router import LLMResponse, LLMRouter
from llm.llm_role import LLMRole


def _make_http_error(status_code: int) -> httpx.HTTPStatusError:
    """Forge un httpx.HTTPStatusError avec le status_code voulu."""
    request = httpx.Request("POST", "https://example.com/v1/chat/completions")
    response = httpx.Response(
        status_code=status_code, request=request,
        text="Request too large ... ITPM: Limit 7000, Requested 9000",
    )
    return httpx.HTTPStatusError(
        f"HTTP {status_code}", request=request, response=response,
    )


@pytest.fixture
def no_sleep(monkeypatch):
    """Évite l'attente 1s entre fallbacks dans complete()."""
    monkeypatch.setattr("llm.llm_router.time.sleep", lambda *a, **kw: None)


def test_groq_413_skips_other_groq(monkeypatch, no_sleep):
    router = LLMRouter()
    calls: list[str] = []

    def fake_call(self, prompt, provider_cfg, temperature, max_tokens):
        provider = provider_cfg["provider"]
        calls.append(provider)
        if provider.startswith("groq"):
            raise _make_http_error(413)
        return LLMResponse(content="ok", metadata={"provider": provider})

    monkeypatch.setattr(LLMRouter, "_call", fake_call)

    result = router.complete("test", role=LLMRole.CHAT)

    assert [c for c in calls if c.startswith("groq")] == ["groq"]
    assert result.metadata["provider"] == "deepseek"
    assert router._negative_cache == {}
