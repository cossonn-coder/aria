# tests/memory/test_idempotent_writer.py
#
# Tests unitaires de _idempotent_doc_id.
# Aucun accès ChromaDB — fonction pure testée en isolation.

import memory.mempalace_writer as w


def test_same_text_same_minute_yields_same_id():
    a = w._idempotent_doc_id("hello", "intent-1")
    b = w._idempotent_doc_id("hello", "intent-1")
    assert a == b


def test_different_minute_yields_different_id(monkeypatch):
    monkeypatch.setattr(w.time, "time", lambda: 1700000000.0)
    a = w._idempotent_doc_id("hello", "intent-1")
    monkeypatch.setattr(w.time, "time", lambda: 1700000060.0)
    b = w._idempotent_doc_id("hello", "intent-1")
    assert a != b


def test_different_intent_yields_different_id():
    a = w._idempotent_doc_id("hello", "intent-1")
    b = w._idempotent_doc_id("hello", "intent-2")
    assert a != b


def test_different_text_yields_different_id():
    a = w._idempotent_doc_id("hello", "intent-1")
    b = w._idempotent_doc_id("world", "intent-1")
    assert a != b
