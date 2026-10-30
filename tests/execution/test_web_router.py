# tests/execution/test_web_router.py
#
# Tests du WebExecutionRouter (sprint 22, tronçon 01) — fakes, pas de réseau.

from unittest.mock import MagicMock

import pytest

import execution.routers.web_router as web_router_mod
from execution.routers.web_router import WebExecutionRouter


@pytest.fixture(autouse=True)
def write_document_mock(monkeypatch):
    # Fiche document (sprint 43) : jamais écrite dans le palace par ces tests.
    mock = MagicMock()
    monkeypatch.setattr(web_router_mod, "write_document", mock)
    return mock


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


# ── FILE_READ (sprint 42, tronçon 01) ────────────────────────────────────────

def _file_payload(path, caption=None):
    return {"op_type": "file_read",
            "content": {"file_path": str(path), "file_name": path.name, "caption": caption},
            "metadata": {"chat_id": 42}}


def test_file_read_short_file_delegates_digest(tmp_path):
    p = tmp_path / "uid_notes.txt"
    p.write_text("Notes courtes.\nFin.", encoding="utf-8")
    router, llm_exec = _make_router()
    router.llm_router.complete.return_value = MagicMock(content="LA SYNTHÈSE", usage=None)

    router.execute(_file_payload(p))

    content = llm_exec.execute.call_args.args[0]["content"]
    assert "Synthèse du fichier « uid_notes.txt »" in content
    assert "LA SYNTHÈSE" in content
    assert "[Lecture partielle :" not in content
    assert "Notes courtes." in router.llm_router.complete.call_args.kwargs["prompt"]


def test_file_read_long_file_marks_path_then_resumes_from_disk(tmp_path):
    p = tmp_path / "uid_long.txt"
    p.write_text(("x" * 999 + "\n") * 250, encoding="utf-8")  # 250 000 car.
    router, llm_exec = _make_router()
    router.llm_router.complete.return_value = MagicMock(content="S", usage=None)

    router.execute(_file_payload(p, caption="résume"))

    content = llm_exec.execute.call_args.args[0]["content"]
    marker = next(l for l in content.splitlines() if l.startswith("[Lecture partielle :"))
    assert marker.startswith(f"[Lecture partielle : {p} caractères 0-")

    # « oui » au tour suivant : le marqueur est dans le dernier tour user.
    router.mempalace_bridge.load_conversation_history.return_value = [
        {"role": "user", "content": content},
        {"role": "assistant", "content": "Je lis la suite ?"},
    ]
    router.execute({"op_type": "url_read", "content": "oui", "metadata": {"chat_id": 42}})

    end = int(marker.split("caractères 0-")[1].split(" ")[0])
    prompt = router.llm_router.complete.call_args.kwargs["prompt"]
    assert f"caractères {end}-" in prompt
    assert "Fichier :" in prompt


# ── Fiche document (sprint 43, tronçon 01) ───────────────────────────────────

def test_file_read_writes_document_card_with_full_text(tmp_path, write_document_mock):
    p = tmp_path / "uid_rapport.txt"
    p.write_text("Rapport annuel.\nChiffres clés.", encoding="utf-8")
    router, _ = _make_router()
    router.llm_router.complete.return_value = MagicMock(content="LA SYNTHÈSE", usage=None)
    payload = _file_payload(p)
    payload["content"]["file_name"] = "rapport.txt"

    router.execute(payload)

    fiche, text, source, title = write_document_mock.call_args.args
    assert source == str(p)
    assert title == "rapport.txt"
    assert text == "Rapport annuel.\nChiffres clés."
    lines = fiche.splitlines()
    assert lines[0].startswith("Document « rapport.txt » lu le ")
    assert lines[1] == f"Source : {p}"
    assert lines[2] == "Synthèse : LA SYNTHÈSE"


def test_read_slice_resume_does_not_write_document(tmp_path, write_document_mock):
    p = tmp_path / "uid_long.txt"
    p.write_text(("x" * 999 + "\n") * 250, encoding="utf-8")
    router, _ = _make_router()
    router.llm_router.complete.return_value = MagicMock(content="S", usage=None)

    router._read_slice(str(p), 100_000, "oui", {"chat_id": 42})

    write_document_mock.assert_not_called()


# ── DOC_REREAD (sprint 43, tronçon 02) ───────────────────────────────────────

def test_doc_reread_synthesizes_palace_text_without_extraction(monkeypatch, write_document_mock):
    extract_mock = MagicMock()
    monkeypatch.setattr(web_router_mod, "extract", extract_mock)
    monkeypatch.setattr(web_router_mod, "extract_text", extract_mock)
    router, llm_exec = _make_router()
    bridge = router.mempalace_bridge
    bridge.load_conversation_history.return_value = [
        {"role": "user", "content": "où est la perceuse ?"},
        {"role": "assistant", "content": "Je ne sais pas. Veux-tu que je relise « inventaire.pdf » ?"},
    ]
    bridge.find_documents.return_value = [{
        "text": "Document « inventaire.pdf » lu le 2026-10-30\nSource : /tmp/inv.pdf\nSynthèse : outils",
    }]
    bridge.load_document_text.return_value = {"title": "inventaire.pdf", "text": "perceuse : garage, étagère 2"}
    router.llm_router.complete.return_value = MagicMock(content="Au garage.", usage=None)

    router.execute({"op_type": "doc_reread", "content": "oui", "metadata": {"chat_id": 42}})

    bridge.find_documents.assert_called_once_with("inventaire.pdf")
    bridge.load_document_text.assert_called_once_with("/tmp/inv.pdf")
    prompt = router.llm_router.complete.call_args.kwargs["prompt"]
    assert "perceuse : garage, étagère 2" in prompt
    assert "où est la perceuse ?" in prompt
    extract_mock.assert_not_called()
    write_document_mock.assert_not_called()
    assert llm_exec.execute.call_args.args[0]["metadata"]["skip_intent"] is True


def test_doc_reread_no_matching_document_answers_not_found():
    router, llm_exec = _make_router()
    bridge = router.mempalace_bridge
    bridge.find_documents.return_value = []

    router.execute({"op_type": "doc_reread", "content": "relis le document sur les impôts",
                    "metadata": {"chat_id": 42}})

    bridge.load_document_text.assert_not_called()
    assert "Aucun document correspondant" in llm_exec.execute.call_args.args[0]["content"]


# ── WEB_RESEARCH (sprint 45, tronçon 01) ─────────────────────────────────────

def test_research_nominal_reads_pages_writes_report_and_delegates(monkeypatch, write_document_mock):
    results = {
        "rotation cultures": [
            {"title": "A", "url": "https://a.ex/1", "content": "extrait A"},
            {"title": "B", "url": "https://b.ex/2", "content": "extrait B"},
        ],
        "rotation potager familles": [
            {"title": "A", "url": "https://a.ex/1", "content": "extrait A"},
            {"title": "C", "url": "https://c.ex/3", "content": "extrait C"},
        ],
    }
    monkeypatch.setattr(web_router_mod, "search", lambda q: results[q])
    extracted = []
    def _extract(url):
        extracted.append(url)
        return {"title": "T", "url": url, "content": f"texte de {url}"}
    monkeypatch.setattr(web_router_mod, "extract", _extract)
    router, llm_exec = _make_router()
    router.mempalace_bridge.retrieve_memories.return_value = {"hits": [{"text": "souvenir"}]}
    router.llm_router.complete.side_effect = [
        MagicMock(content="1. rotation cultures\n- rotation potager familles\n"),
        MagicMock(content="LE RAPPORT https://a.ex/1", usage={"completion_tokens": 900}),
    ]

    result = router.execute({"op_type": "web_research",
                             "content": "fais une recherche sur la rotation des cultures",
                             "metadata": {"chat_id": 42}})

    # 1er résultat de chaque requête, puis les suivants, sans doublon
    assert extracted == ["https://a.ex/1", "https://b.ex/2", "https://c.ex/3"]
    delegated = llm_exec.execute.call_args.args[0]
    assert result == {"text": "réponse"}
    assert delegated["op_type"] == "reasoning"
    assert delegated["metadata"]["skip_intent"] is True
    assert "LE RAPPORT" in delegated["content"]
    write_document_mock.assert_called_once()
    fiche, text, source, name = write_document_mock.call_args.args
    assert source.startswith("recherche:") and " " not in source
    assert "Source : recherche:" in fiche
    assert text == "LE RAPPORT https://a.ex/1"
    assert name == "Recherche : la rotation des cultures"
    assert router.llm_router.complete.call_args_list[1].kwargs["max_tokens"] == 3000
