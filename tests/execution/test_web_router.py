# tests/execution/test_web_router.py
#
# Tests du WebExecutionRouter (sprint 22, tronçon 01) — fakes, pas de réseau.

from unittest.mock import MagicMock

import pytest

import execution.routers.web_router as web_router_mod
from execution.routers.web_router import WebExecutionRouter


def _make_router():
    llm_router = MagicMock()
    llm_router.complete.return_value = MagicMock(content="météo Lyon demain")
    bridge = MagicMock()
    bridge.load_conversation_history.return_value = []
    llm_exec = MagicMock()
    llm_exec.execute.return_value = {"text": "réponse"}
    router = WebExecutionRouter(
        llm_router=llm_router, mempalace_bridge=bridge, llm_execution_router=llm_exec,
    )
    return router, llm_exec


def _payload():
    return {"op_type": "web_search", "content": "cherche en ligne la météo à Lyon",
            "metadata": {"chat_id": 42}}


def test_search_nominal_delegates_enriched_reasoning(monkeypatch):
    monkeypatch.setattr(web_router_mod, "search", lambda q: [
        {"title": "Météo Lyon", "url": "https://a.example/lyon", "content": "Soleil."},
        {"title": "Prévisions", "url": "https://b.example/prev", "content": "Pluie."},
    ])
    router, llm_exec = _make_router()

    result = router.execute(_payload())

    delegated = llm_exec.execute.call_args.args[0]
    assert result == {"text": "réponse"}
    assert delegated["op_type"] == "reasoning"
    assert delegated["metadata"]["skip_intent"] is True
    assert "https://a.example/lyon" in delegated["content"]
    assert "https://b.example/prev" in delegated["content"]
    assert "cherche en ligne la météo à Lyon" in delegated["content"]


def test_search_failure_delegates_unavailable_notice(monkeypatch):
    def _boom(q):
        raise RuntimeError("down")
    monkeypatch.setattr(web_router_mod, "search", _boom)
    router, llm_exec = _make_router()

    router.execute(_payload())

    assert "Recherche web indisponible" in llm_exec.execute.call_args.args[0]["content"]
