# tests/llm/test_empty_response_fallback.py
#
# Sprint 18 / tronçon 01 : réponse vide = échec → fallback, et fusion de
# l'entrée `extra` d'une chaîne dans le payload OpenAI-compatible.
# Convention test_negative_cache.py : imports absolus, monkeypatch sur httpx.post.

import httpx

from llm.llm_role import LLMRole
from llm.llm_router import ROUTING_TABLE, LLMRouter


def _cfg(provider: str, extra: dict | None = None) -> dict:
    cfg = {
        "provider": provider,
        "model": f"{provider}-model",
        "base_url": f"https://{provider}.test/v1",
        "api_key": lambda: "fake-key",
    }
    if extra is not None:
        cfg["extra"] = extra
    return cfg


def _install_post(monkeypatch, contents: dict, calls: list):
    """httpx.post factice : renvoie le content associé à l'URL appelée."""

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append((url, json))
        content = next(c for base, c in contents.items() if url.startswith(base))
        body = {"choices": [{"message": {"content": content},
                             "finish_reason": "length"}], "usage": {}}
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr("httpx.post", fake_post)
    monkeypatch.setattr("time.sleep", lambda s: None)


def test_empty_content_falls_back_to_next_provider(monkeypatch):
    monkeypatch.setitem(ROUTING_TABLE, LLMRole.CHAT, [_cfg("a"), _cfg("b")])
    calls: list = []
    _install_post(monkeypatch, {"https://a.test": "  ", "https://b.test": "ok"}, calls)

    result = LLMRouter().complete(prompt="hello", role=LLMRole.CHAT)

    assert result.content == "ok"
    assert result.metadata["provider"] == "b"
    assert len(calls) == 2


def test_extra_is_merged_into_payload(monkeypatch):
    extra = {"thinking": {"type": "disabled"}}
    monkeypatch.setitem(ROUTING_TABLE, LLMRole.CHAT, [_cfg("a", extra)])
    calls: list = []
    _install_post(monkeypatch, {"https://a.test": "ok"}, calls)

    LLMRouter().complete(prompt="hello", role=LLMRole.CHAT)

    assert calls[0][1]["thinking"] == {"type": "disabled"}
