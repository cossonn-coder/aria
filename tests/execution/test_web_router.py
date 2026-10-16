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


# ── URL_READ (sprint 23, tronçon 01) ─────────────────────────────────────────

from llm.llm_role import LLMRole

_URL = "https://ex.fr/page"


def _url_payload():
    return {"op_type": "url_read", "content": f"résume {_URL} stp", "metadata": {"chat_id": 42}}


def _fake_extract(text):
    return lambda url: {"title": "Titre", "url": url, "content": text}


def test_url_read_short_page_delegates_digest(monkeypatch):
    monkeypatch.setattr(web_router_mod, "extract", _fake_extract("Page courte.\nFin."))
    router, llm_exec = _make_router()
    router.llm_router.complete.return_value = MagicMock(content="LA SYNTHÈSE", usage={"completion_tokens": 50})

    result = router.execute(_url_payload())

    delegated = llm_exec.execute.call_args.args[0]
    assert result == {"text": "réponse"}
    assert delegated["op_type"] == "reasoning"
    assert delegated["metadata"]["skip_intent"] is True
    assert "LA SYNTHÈSE" in delegated["content"]
    assert _URL in delegated["content"]
    assert "[Lecture partielle :" not in delegated["content"]
    assert router.llm_router.complete.call_args.kwargs["role"] == LLMRole.DIGEST


def test_url_read_long_page_cuts_at_paragraph(monkeypatch):
    text = ("x" * 999 + "\n") * 250  # 250 000 car., paragraphes de 1 000
    monkeypatch.setattr(web_router_mod, "extract", _fake_extract(text))
    router, llm_exec = _make_router()
    router.llm_router.complete.return_value = MagicMock(content="S", usage=None)

    router.execute(_url_payload())

    content = llm_exec.execute.call_args.args[0]["content"]
    marker = next(l for l in content.splitlines() if l.startswith("[Lecture partielle :"))
    end = int(marker.split("caractères 0-")[1].split(" ")[0])
    assert end <= 100_000
    assert text[end - 1] == "\n" or text[end] == "\n"
    assert marker == f"[Lecture partielle : {_URL} caractères 0-{end} sur 250000]"


def test_url_read_extract_failure_delegates_notice(monkeypatch):
    def _boom(url):
        raise RuntimeError("down")
    monkeypatch.setattr(web_router_mod, "extract", _boom)
    router, llm_exec = _make_router()

    router.execute(_url_payload())

    assert "Page illisible" in llm_exec.execute.call_args.args[0]["content"]


# ── Reprise « lis la suite » (sprint 23, tronçon 02) ─────────────────────────

def test_url_read_resume_reads_next_slice(monkeypatch):
    text = "a" * 99_000 + "DEBUT_SUITE" + "b" * 150_989  # 250 000 car.
    extracted = []
    def _extract(url):
        extracted.append(url)
        return {"title": "Titre", "url": url, "content": text}
    monkeypatch.setattr(web_router_mod, "extract", _extract)
    router, llm_exec = _make_router()
    router.mempalace_bridge.load_conversation_history.return_value = [
        {"role": "user", "content": f"[Lecture partielle : {_URL} caractères 0-99000 sur 250000]\n\nrésume {_URL}"},
        {"role": "assistant", "content": "Je lis la suite ?"},
    ]
    router.llm_router.complete.return_value = MagicMock(content="S2", usage=None)

    router.execute({"op_type": "url_read", "content": "oui", "metadata": {"chat_id": 42}})

    assert extracted == [_URL]
    prompt = router.llm_router.complete.call_args.kwargs["prompt"]
    assert "caractères 99000-" in prompt
    assert prompt.split("sur 250000) :\n")[1].startswith("DEBUT_SUITE")
    content = llm_exec.execute.call_args.args[0]["content"]
    assert f"[Lecture partielle : {_URL} caractères 99000-" in content
