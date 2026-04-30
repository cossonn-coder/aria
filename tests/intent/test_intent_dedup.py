# tests/intent/test_intent_dedup.py
#
# Tests unitaires Bug E — déduplication d'intents et formule de scoring.
#
# IntentRecallEngine testé via resolve() avec embedder MagicMock.
# IntentEngine testé via apply() avec load/save mockés et MockEmbedder.

import math
import numpy as np
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from intent.intent_recall_engine import IntentRecallEngine, RecallDecision
from intent.intent_engine import IntentEngine


# ── Embedders de test ─────────────────────────────────────────────────────────

class MockEmbedder:
    """
    Embedder déterministe pour tests IntentEngine.
    Retourne des vecteurs unitaires préétablis selon le texte.
    """
    PRESETS = {
        "jardinage légumes": [1.0, 0.0, 0.0],
        # cosine avec [1,0,0] ≈ 0.9 (> seuil 0.55)
        "carottes dans jardin": [0.9, math.sqrt(1 - 0.81), 0.0],
        # cosine avec [1,0,0] = 0.0 (< seuil 0.55)
        "activité totalement différente": [0.0, 0.0, 1.0],
    }
    _DEFAULT = [0.5, 0.5, 0.0]

    def encode(self, texts):
        results = []
        for t in texts:
            v = np.array(self.PRESETS.get(t, self._DEFAULT), dtype=np.float32)
            norm = np.linalg.norm(v)
            results.append((v / norm if norm > 0 else v).tolist())
        return results


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def recall_engine():
    embedder = MagicMock()
    return IntentRecallEngine(embedder, threshold=0.45), embedder


@pytest.fixture
def engine():
    embedder = MockEmbedder()
    with patch("intent.intent_engine.load_intents", return_value={}), \
         patch("intent.intent_engine.save_intents"):
        e = IntentEngine(embedder)
    return embedder, e


# ── Tests formule de scoring ──────────────────────────────────────────────────

def test_formula_no_penalty_when_no_memory(recall_engine):
    """Sans mémoire, le score final doit égaler le cosine — pas 0.8×cosine."""
    engine, embedder = recall_engine
    embedder.encode.return_value = [[1.0, 0.0, 0.0]]

    intent = SimpleNamespace(
        id="x1",
        status="active",
        embedding=[0.6, 0.8, 0.0],  # cosine avec [1,0,0] = 0.6
    )

    _, scored = engine.resolve("msg", [intent], memory_context=None)

    assert scored, "scored doit contenir au moins un résultat"
    score = scored[0][1]
    assert abs(score - 0.6) < 0.01, f"attendu ≈0.6, obtenu {score:.4f}"
    assert abs(score - 0.48) > 0.05, "score ne doit PAS égaler 0.8×cosine (ancienne formule)"


def test_formula_boost_capped_at_1(recall_engine):
    """cosine élevé + boost mémoire ne doit pas dépasser 1.0."""
    engine, embedder = recall_engine
    embedder.encode.return_value = [[1.0, 0.0, 0.0]]

    # cosine([1,0,0], [0.95, 0.312, 0]) ≈ 0.95
    intent = SimpleNamespace(
        id="x1",
        status="active",
        embedding=[0.95, 0.312, 0.0],
    )
    # 2 hits room=x1 → mem_score normalisé = 1.0
    memory_context = {"hits": [{"room": "x1"}, {"room": "x1"}]}

    _, scored = engine.resolve("msg", [intent], memory_context=memory_context)

    score = scored[0][1]
    assert score <= 1.0, f"score dépasse 1.0 : {score}"
    assert abs(score - 1.0) < 0.01, f"attendu ≈1.0 après clamp, obtenu {score:.4f}"


# ── Tests déduplication IntentEngine ─────────────────────────────────────────

def test_exact_name_dedup(engine):
    """Nom canonique identique (insensible à la casse) → rattacher, pas créer."""
    _, eng = engine
    existing = eng._create("Jardinage Légumes")

    decision = RecallDecision(action="create")
    result = eng.apply(decision, message="jardinage", intent_name="jardinage légumes")

    assert result.id == existing.id, "doit rattacher à l'intent existant"
    assert len(eng.intents) == 1, "aucun nouvel intent ne doit être créé"


def test_semantic_name_dedup(engine):
    """Nom sémantiquement proche (cosine > 0.55) → rattacher, pas créer."""
    _, eng = engine
    existing = eng._create("jardinage légumes")

    decision = RecallDecision(action="create")
    result = eng.apply(decision, message="carottes", intent_name="carottes dans jardin")

    assert result.id == existing.id, "doit rattacher à l'intent sémantiquement proche"
    assert len(eng.intents) == 1, "aucun nouvel intent ne doit être créé"


def test_below_threshold_creates_new(engine):
    """Nom sémantiquement éloigné (cosine < 0.55) → créer un nouvel intent."""
    _, eng = engine
    eng._create("jardinage légumes")

    decision = RecallDecision(action="create")
    result = eng.apply(
        decision,
        message="nouvelle activité",
        intent_name="activité totalement différente",
    )

    assert len(eng.intents) == 2, "un nouvel intent doit être créé"
    assert result.id != list(eng.intents.keys())[0], "l'intent retourné doit être le nouveau"
