# tests/llm/test_negative_cache.py
#
# Garde-fous du cache négatif providers LLM (sprint 5 / dette #8).
#
# Couvre :
#   D.1 — un 429 ajoute une entrée dans le cache.
#   D.2 — un provider en cache n'est pas tenté en HTTP.
#   D.3 — une entrée expirée est ignorée et purgée au lookup.
#   D.4 — un 5xx ne déclenche pas la mise en cache.
#
# Cf. docs/sprint5/audit_negative_cache.md pour le design.

import time

import httpx
import pytest

from llm.llm_router import LLMResponse, LLMRouter
from llm.llm_role import LLMRole


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_http_error(status_code: int) -> httpx.HTTPStatusError:
    """Forge un httpx.HTTPStatusError avec le status_code voulu."""
    request = httpx.Request("POST", "https://example.com/v1/chat/completions")
    response = httpx.Response(status_code=status_code, request=request)
    return httpx.HTTPStatusError(
        f"HTTP {status_code}", request=request, response=response,
    )


def _success_response(provider: str = "groq_2") -> LLMResponse:
    return LLMResponse(
        content="ok",
        metadata={"provider": provider, "model": "fake"},
    )


@pytest.fixture
def no_sleep(monkeypatch):
    """Évite l'attente 1s entre fallbacks dans complete()."""
    monkeypatch.setattr("llm.llm_router.time.sleep", lambda *a, **kw: None)


# ── D.1 — 429 → entrée en cache ──────────────────────────────────────────────

def test_429_inserts_cache_entry(monkeypatch, no_sleep):
    """Un 429 sur le premier provider doit créer une entrée cache valide
    et permettre au suivant de répondre."""
    router = LLMRouter()

    def fake_call(self, prompt, provider_cfg, temperature, max_tokens):
        if provider_cfg["provider"] == "groq":
            raise _make_http_error(429)
        return _success_response(provider_cfg["provider"])

    monkeypatch.setattr(LLMRouter, "_call", fake_call)

    result = router.complete("test", role=LLMRole.CHAT)

    assert result.content == "ok"
    assert "groq" in router._negative_cache, "le 429 doit être caché"
    assert router._negative_cache["groq"] > time.monotonic(), (
        "l'entrée doit avoir un TTL futur"
    )


# ── D.2 — provider caché → skip ──────────────────────────────────────────────

def test_cached_provider_is_skipped(monkeypatch, no_sleep):
    """Un provider déjà dans le cache n'est pas tenté en HTTP."""
    router = LLMRouter()
    # Préremplit avec un TTL futur (60 s).
    router._negative_cache["groq"] = time.monotonic() + 60.0

    calls: list[str] = []

    def fake_call(self, prompt, provider_cfg, temperature, max_tokens):
        calls.append(provider_cfg["provider"])
        return _success_response(provider_cfg["provider"])

    monkeypatch.setattr(LLMRouter, "_call", fake_call)

    result = router.complete("test", role=LLMRole.CHAT)

    assert result.content == "ok"
    assert "groq" not in calls, "groq devait être skippé sans tentative HTTP"
    assert calls[0] == "groq_2", "le provider suivant doit prendre le relais"


# ── D.3 — entrée expirée → retry ─────────────────────────────────────────────

def test_cached_entry_expires(monkeypatch, no_sleep):
    """Une entrée dans le passé (expirée) est ignorée et purgée."""
    router = LLMRouter()
    # TTL dans le passé → considérée expirée.
    router._negative_cache["groq"] = time.monotonic() - 1.0

    calls: list[str] = []

    def fake_call(self, prompt, provider_cfg, temperature, max_tokens):
        calls.append(provider_cfg["provider"])
        return _success_response(provider_cfg["provider"])

    monkeypatch.setattr(LLMRouter, "_call", fake_call)

    result = router.complete("test", role=LLMRole.CHAT)

    assert result.content == "ok"
    assert calls[0] == "groq", "groq devait être ré-essayé après expiration"
    assert "groq" not in router._negative_cache, (
        "l'entrée expirée doit être purgée au lookup"
    )


# ── D.4 — 500 → pas de cache ─────────────────────────────────────────────────

def test_500_does_not_cache(monkeypatch, no_sleep):
    """Un 500 ne doit PAS bloquer le provider 5 min — c'est un crash
    transitoire, pas un quota."""
    router = LLMRouter()

    def fake_call(self, prompt, provider_cfg, temperature, max_tokens):
        if provider_cfg["provider"] == "groq":
            raise _make_http_error(500)
        return _success_response(provider_cfg["provider"])

    monkeypatch.setattr(LLMRouter, "_call", fake_call)

    result = router.complete("test", role=LLMRole.CHAT)

    assert result.content == "ok"
    assert "groq" not in router._negative_cache, (
        "un 500 ne doit pas alimenter le cache négatif"
    )


# ── Bonus — exception non-HTTP (timeout, connect error) → pas de cache ───────

def test_generic_exception_does_not_cache(monkeypatch, no_sleep):
    """Une exception non-HTTPStatusError (timeout, connect, etc.)
    ne doit pas alimenter le cache."""
    router = LLMRouter()

    def fake_call(self, prompt, provider_cfg, temperature, max_tokens):
        if provider_cfg["provider"] == "groq":
            raise httpx.ConnectError("network down")
        return _success_response(provider_cfg["provider"])

    monkeypatch.setattr(LLMRouter, "_call", fake_call)

    result = router.complete("test", role=LLMRole.CHAT)

    assert result.content == "ok"
    assert "groq" not in router._negative_cache
