# tests/memory/test_writer.py
#
# Tests unitaires de aria/memory/writer.py.
# Aucun accès ChromaDB réel — FakeCollection capture les appels upsert.

import json
import pytest
from unittest.mock import patch

import memory.writer as w
from images.image_types import ImageArtifact


# ── FakeCollection ────────────────────────────────────────────────────────────

class FakeCollection:
    def __init__(self):
        self.calls = []

    def upsert(self, documents, ids, metadatas):
        self.calls.append({
            "documents": documents,
            "ids": ids,
            "metadatas": metadatas,
        })

    @property
    def last_meta(self) -> dict:
        return self.calls[-1]["metadatas"][0]

    @property
    def last_doc(self) -> str:
        return self.calls[-1]["documents"][0]

    @property
    def last_id(self) -> str:
        return self.calls[-1]["ids"][0]


@pytest.fixture
def fake_col():
    col = FakeCollection()
    with patch("memory.writer.get_collection", return_value=col):
        yield col


# ── 1. write_interaction — wing toujours aria_episodic ───────────────────────

def test_write_interaction_wing_is_always_episodic(fake_col):
    w.write_interaction("msg", "intent-1")
    assert fake_col.last_meta["wing"] == "aria_episodic"


# ── 2. write_interaction — room = intent_id ──────────────────────────────────

def test_write_interaction_room_is_intent_id(fake_col):
    w.write_interaction("msg", "intent-42")
    assert fake_col.last_meta["room"] == "intent-42"


# ── 3. write_interaction — type = interaction ────────────────────────────────

def test_write_interaction_type_is_interaction(fake_col):
    w.write_interaction("msg", "intent-1")
    assert fake_col.last_meta["type"] == "interaction"


# ── 4. write_interaction — extra ne peut pas overrider wing (anti-régression W4)

def test_write_interaction_extra_cannot_override_wing(fake_col):
    """Régression directe du bug W4 (sprint 3.1 / dette #11).
    Passer wing='aria' dans extra ne doit pas corrompre la destination."""
    w.write_interaction(
        "msg",
        "intent-1",
        extra={"wing": "aria", "room": "wrong-room", "type": "wrong-type"},
    )
    assert fake_col.last_meta["wing"] == "aria_episodic"
    assert fake_col.last_meta["room"] == "intent-1"
    assert fake_col.last_meta["type"] == "interaction"


# ── 5. write_interaction — idempotence dans la même minute ───────────────────

def test_write_interaction_idempotence_same_minute(fake_col, monkeypatch):
    monkeypatch.setattr(w.time, "time", lambda: 1700000000.0)
    w.write_interaction("hello", "intent-1")
    id_a = fake_col.last_id
    w.write_interaction("hello", "intent-1")
    id_b = fake_col.last_id
    assert id_a == id_b, "même texte + même intent dans la même minute → même doc_id"


# ── 6. write_image_artifact — IMAGE_INPUT : wing et type ─────────────────────

def test_write_image_artifact_input_wing_and_type(fake_col):
    artifact = ImageArtifact(
        source="input",
        caption="une photo de jardin",
        path="/tmp/img.jpg",
    )
    w.write_image_artifact(artifact, intent_id="intent-x")
    assert fake_col.last_meta["wing"] == "aria_episodic"
    assert fake_col.last_meta["type"] == "image_input"


# ── 7. write_image_artifact — IMAGE_GENERATED : wing et type ─────────────────

def test_write_image_artifact_generated_wing_and_type(fake_col):
    artifact = ImageArtifact(
        source="generated",
        prompt="un jardin en aquarelle",
        path="/tmp/gen.png",
    )
    w.write_image_artifact(artifact, intent_id="intent-x")
    assert fake_col.last_meta["wing"] == "aria_episodic"
    assert fake_col.last_meta["type"] == "image_generated"


# ── 8. write_image_artifact — intent_id=None → room="general" ────────────────

def test_write_image_artifact_no_intent_room_is_general(fake_col):
    artifact = ImageArtifact(source="input", caption="photo sans contexte")
    w.write_image_artifact(artifact, intent_id=None)
    assert fake_col.last_meta["room"] == "general"


# ── 9. write_semantic_fact — wing aria_semantic et room = subject ─────────────

def test_write_semantic_fact_wing_and_room(fake_col):
    w.write_semantic_fact("Nico est allergique au gluten", subject="santé")
    assert fake_col.last_meta["wing"] == "aria_semantic"
    assert fake_col.last_meta["room"] == "santé"
    assert fake_col.last_meta["type"] == "semantic_fact"


# ── 10. write_classifier_cache — wing, room et format document JSON ───────────

def test_write_classifier_cache_wing_and_document_format(fake_col):
    w.write_classifier_cache("Tu te rappelles des carottes ?", "fact_recall")
    meta = fake_col.last_meta
    assert meta["wing"] == "aria_classifier"
    assert meta["room"] == "classifier_cache"
    assert meta["type"] == "classifier_cache"
    # le document doit être parseable en JSON avec les bons champs
    data = json.loads(fake_col.last_doc)
    assert data["message"] == "Tu te rappelles des carottes ?"
    assert data["operation"] == "fact_recall"
