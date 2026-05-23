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


# ── 10. write_classifier_cache — schéma post-T2 (dette #20) ───────────────────

def test_write_classifier_cache_wing_and_document_format(fake_col):
    """Post-T2 sprint 5 : document = message brut, operation portée par room.
    Cf. docs/sprint5/audit_cache_classifier.md §4 (Option A)."""
    w.write_classifier_cache("Tu te rappelles des carottes ?", "fact_recall")
    meta = fake_col.last_meta
    assert meta["wing"] == "aria_classifier"
    assert meta["room"] == "fact_recall"
    assert meta["type"] == "classifier_cache"
    # Document = message brut (plus de JSON sérialisé)
    assert fake_col.last_doc == "Tu te rappelles des carottes ?"


# ── 11. write_classifier_cache — enum non sérialisable → TypeError visible ────

def test_write_classifier_cache_rejects_non_string_operation(fake_col):
    """Garde-fou : passer un enum (ou autre objet non-str) à operation
    produit une TypeError visible, pas un trou silencieux.
    Documente le contrat : operation doit être str (.value côté caller)."""
    from enum import Enum
    class FakeEnum(Enum):
        FOO = "foo"
    with pytest.raises(TypeError):
        w.write_classifier_cache("msg", FakeEnum.FOO)


# ── 12. write_classifier_cache — garde-fou anti-régression dette #20 ──────────

def test_write_classifier_cache_indexes_message_brut(fake_col):
    """Garde-fou direct du fix dette #20 (sprint 5 / T2).

    Régression à éviter : retomber dans le format JSON sérialisé qui
    décalait l'embedding écrit vs l'embedding query (cosine 0.47-0.60
    sur des messages identiques, jamais de hit > 0.92).

    Vérifie :
      - document indexé == message brut (pas un JSON)
      - metadata.room == operation (Option A : pas de metadata.operation)
      - aucune clé "message" ou "operation" ne pollue metadata
    """
    msg = "tu te rappelles des carottes ?"
    w.write_classifier_cache(msg, "fact_recall")

    # Document = message brut
    assert fake_col.last_doc == msg, (
        f"Document doit être le message brut, pas un JSON. Got: {fake_col.last_doc!r}"
    )
    # Tentative de json.loads doit échouer (sauf coïncidence : un message
    # qui ressemble à du JSON valide). Pour ce message-test, échec garanti.
    with pytest.raises((json.JSONDecodeError, ValueError)):
        json.loads(fake_col.last_doc)

    # operation portée par room
    assert fake_col.last_meta["room"] == "fact_recall"
    # Pas de pollution metadata
    assert "message" not in fake_col.last_meta
    assert "operation" not in fake_col.last_meta


# ── 13. write_conversation_turn — wing toujours aria_conversation ────────────

def test_write_conversation_turn_wing_is_aria_conversation(fake_col):
    w.write_conversation_turn("conv-1", "user", "salut")
    assert fake_col.last_meta["wing"] == "aria_conversation"


# ── 14. write_conversation_turn — room = conversation_key ────────────────────

def test_write_conversation_turn_room_is_conversation_key(fake_col):
    w.write_conversation_turn("conv-42", "user", "salut")
    assert fake_col.last_meta["room"] == "conv-42"


# ── 15. write_conversation_turn — type = conversation_turn ───────────────────

def test_write_conversation_turn_type_is_conversation_turn(fake_col):
    w.write_conversation_turn("conv-1", "assistant", "réponse")
    assert fake_col.last_meta["type"] == "conversation_turn"


# ── 16. write_conversation_turn — role "user" accepté et porté en meta ───────

def test_write_conversation_turn_role_user_accepted(fake_col):
    w.write_conversation_turn("conv-1", "user", "question")
    assert fake_col.last_meta["role"] == "user"
    assert fake_col.last_doc == "question"


# ── 17. write_conversation_turn — role "assistant" accepté et porté en meta ──

def test_write_conversation_turn_role_assistant_accepted(fake_col):
    w.write_conversation_turn("conv-1", "assistant", "réponse")
    assert fake_col.last_meta["role"] == "assistant"
    assert fake_col.last_doc == "réponse"


# ── 18. write_conversation_turn — role invalide → ValueError ─────────────────

@pytest.mark.parametrize("bad_role", ["system", "foo", "", "User", "ASSISTANT", "tool"])
def test_write_conversation_turn_role_invalid_raises_value_error(fake_col, bad_role):
    """Garde-fou : seuls "user" et "assistant" sont acceptés à ce stade.
    Cf. audit sprint 15 §arbitrage 2 (pas de "system" délibérément)."""
    with pytest.raises(ValueError):
        w.write_conversation_turn("conv-1", bad_role, "content")


# ── 19. write_conversation_turn — extra ne peut pas overrider wing (W4) ──────

def test_write_conversation_turn_extra_cannot_override_wing(fake_col):
    """Régression directe du bug W4 (sprint 3.1 / dette #11).
    Passer wing/room/type/role dans extra ne doit pas corrompre la
    destination ni le rôle métier — wing/room/type/role sont posés
    APRÈS le spread."""
    w.write_conversation_turn(
        "conv-1",
        "user",
        "salut",
        extra={
            "wing": "aria",
            "room": "wrong-room",
            "type": "wrong-type",
            "role": "assistant",
        },
    )
    assert fake_col.last_meta["wing"] == "aria_conversation"
    assert fake_col.last_meta["room"] == "conv-1"
    assert fake_col.last_meta["type"] == "conversation_turn"
    assert fake_col.last_meta["role"] == "user"
