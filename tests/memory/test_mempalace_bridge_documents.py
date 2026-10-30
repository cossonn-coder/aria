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
