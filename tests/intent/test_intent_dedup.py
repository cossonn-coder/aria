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


# ── Régression bug E — embedder réel ─────────────────────────────────────────

def test_regression_bug_e_real_embeddings():
    """
    Régression bug E end-to-end via resolve().
    Avec le vrai embedder, le message "Pourquoi ils ne germent pas"
    doit franchir le seuil 0.45 face à un intent "problème de germination"
    existant — démontrant que la formule corrigée (cosine + boost)
    fait le job sur le cas réel qui a déclenché le sprint.

    Ce test utilise SentenceTransformer réel — pas de mock — pour
    protéger contre une régression silencieuse en cas de changement
    d'embedder ou de modèle.

    # MESURE OBSERVÉE (avril 2026, all-MiniLM-L6-v2) : score = 0.4889 sans mem_score.
    # Marge de 0.04 au-dessus du seuil — fragile à un changement d'embedder.
    # En prod, le boost mem_score (+0.2 max) compense largement quand l'intent a
    # déjà de la mémoire ; le test isole volontairement le cas le plus défavorable
    # (memory_context=None) pour faire échec si le scoring nu se dégrade.
    """
    SentenceTransformer = pytest.importorskip("sentence_transformers").SentenceTransformer

    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    engine = IntentRecallEngine(embedder, threshold=0.45)

    intent_emb = embedder.encode(["problème de germination"])[0].tolist()
    intent = SimpleNamespace(id="x1", status="active", embedding=intent_emb)

    decision, scored = engine.resolve(
        "Pourquoi ils ne germent pas",
        [intent],
        memory_context=None,  # on teste le scoring SANS aide mémoire
    )
    
    assert scored, "scored ne doit pas être vide"
    score = scored[0][1]
    print(f"\n>>> score obtenu = {score:.4f} (seuil = 0.45)")
    assert score >= 0.45, (
        f"régression bug E : score {score:.4f} < 0.45, "
        f"l'attach ne se déclenchera pas"
    )
    assert decision.action == "attach", (
        f"attendu 'attach', obtenu '{decision.action}' (score={score:.4f})"
    )


# ── Rooms non-intent ignorées ─────────────────────────────────────────────────

def test_non_intent_rooms_dont_corrupt_scoring(recall_engine):
    """
    Les hits avec room ∈ {general, knowledge_ingest, ...} (pas un intent_id)
    sont collectés dans mem_score_map mais aucun intent n'ayant cet ID,
    ils ne boostent rien. Ce test gèle ce contrat : un changement futur
    qui filtrerait par room valide ne doit pas casser le comportement,
    et un changement qui les utiliserait à tort doit faire échouer ce test.
    """
    engine, embedder = recall_engine
    embedder.encode.return_value = [[1.0, 0.0, 0.0]]

    intent = SimpleNamespace(id="x1", status="active", embedding=[0.6, 0.8, 0.0])
    memory_context = {"hits": [
        {"room": "general"},
        {"room": "knowledge_ingest"},
        {"room": "agents"},
    ]}

    _, scored = engine.resolve("msg", [intent], memory_context=memory_context)

    # cosine pur attendu (≈0.6), pas de boost car aucun hit ne pointe vers x1
    assert scored, "scored ne doit pas être vide"
    assert abs(scored[0][1] - 0.6) < 0.01, (
        f"score corrompu par rooms non-intent : {scored[0][1]:.4f} (attendu ≈0.6)"
    )
