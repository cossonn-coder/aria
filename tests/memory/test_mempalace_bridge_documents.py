# tests/memory/test_mempalace_bridge_documents.py
#
# Sprint 43 (#137) : load_document_text lit le texte intégral par source.

from memory.mempalace_bridge import MempalaceBridge


def test_load_document_text_returns_title_and_text():
    calls = []

    def fake_get_by_metadata(path, where, include=None):
        calls.append(where)
        return {"ids": ["document_text_k"], "documents": ["texte intégral"],
                "metadatas": [{"title": "inventaire.pdf", "source": "/tmp/inv.pdf"}]}

    bridge = MempalaceBridge(store=None, get_by_metadata=fake_get_by_metadata)

    assert bridge.load_document_text("/tmp/inv.pdf") == {"title": "inventaire.pdf", "text": "texte intégral"}
    assert calls == [{"$and": [{"wing": "aria_documents"}, {"source": "/tmp/inv.pdf"}]}]


# Sprint 44 (#146, #147) : find_documents filtre la room par mots porteurs.

_PAILLAGE = {"text": "Document « Paillage » lu le 2026-10-30\nSource : https://fr.wikipedia.org/wiki/Paillage\n"
                     "Synthèse : couvrir le sol", "room": "documents", "distance": 0.6}
_INVENTAIRE = {"text": "Document « inventaire.pdf » lu le 2026-10-30\nSource : /tmp/inv.pdf\n"
                       "Synthèse : outils du garage", "room": "documents", "distance": 0.5}


def _documents_bridge():
    def fake_search(query, wing, room, n):
        return {"results": [_INVENTAIRE, _PAILLAGE]}
    return MempalaceBridge(store=fake_search)


def test_find_documents_keeps_card_with_keyword():
    assert _documents_bridge().find_documents("que disait la page sur le paillage ?") == [_PAILLAGE]


def test_find_documents_no_match_returns_empty():
    assert _documents_bridge().find_documents("relis le document sur les impôts") == []


def test_find_documents_without_keyword_returns_none():
    assert _documents_bridge().find_documents("relis le document") is None
