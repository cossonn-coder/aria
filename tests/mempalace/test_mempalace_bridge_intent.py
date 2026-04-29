# tests/mempalace/test_mempalace_bridge_intent.py
#
# Tests unitaires de MempalaceBridge — recall ciblé par intent.
#
# Stratégie :
#   MempalaceBridge est instancié avec un store fake (callable).
#   On vérifie que retrieve_by_intent transmet les bons paramètres
#   au store et qu'il ne filtre pas par distance (contrairement à
#   retrieve_memories).

import pytest
from memory.mempalace_bridge import MempalaceBridge


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_bridge(results: list) -> MempalaceBridge:
    """Crée un bridge avec un store fake retournant les résultats fournis."""
    def fake_store(**kwargs):
        return {"results": results}
    return MempalaceBridge(store=fake_store)


def make_bridge_capturing() -> tuple[MempalaceBridge, list]:
    """Crée un bridge dont le store capture les kwargs de chaque appel."""
    captured = []
    def fake_store(**kwargs):
        captured.append(kwargs)
        return {"results": []}
    return MempalaceBridge(store=fake_store), captured


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_retrieve_by_intent_basic():
    """Le résultat doit contenir hits et count cohérents."""
    bridge = make_bridge([
        {"text": "souvenir lié à l'intent", "distance": 0.4},
    ])

    res = bridge.retrieve_by_intent(
        query="test query",
        intent_id="test_intent_123",
    )

    assert isinstance(res, dict)
    assert "hits" in res
    assert "count" in res
    assert res["count"] == len(res["hits"])


def test_retrieve_by_intent_targets_episodic():
    """retrieve_by_intent doit cibler wing='aria_episodic'."""
    bridge, captured = make_bridge_capturing()

    bridge.retrieve_by_intent("query", intent_id="intent-abc")

    assert captured[0]["wing"] == "aria_episodic"


def test_retrieve_by_intent_room_is_intent_id():
    """Le room transmis au store doit être l'intent_id."""
    bridge, captured = make_bridge_capturing()

    bridge.retrieve_by_intent("query", intent_id="intent-jardin-007")

    assert captured[0]["room"] == "intent-jardin-007"


def test_retrieve_by_intent_no_distance_filter():
    """
    retrieve_by_intent ne filtre PAS par distance.

    On veut tout le contexte du projet, même les souvenirs éloignés
    thématiquement mais qui appartiennent au même intent.
    """
    bridge = make_bridge([
        {"text": "proche",       "distance": 0.2},
        {"text": "moins proche", "distance": 0.75},
        {"text": "loin",         "distance": 0.95},
    ])

    result = bridge.retrieve_by_intent("query", intent_id="intent-001")

    assert result["count"] == 3


def test_retrieve_by_intent_empty_results():
    """Un store retournant [] doit produire count=0."""
    bridge = make_bridge([])

    result = bridge.retrieve_by_intent("query", intent_id="intent-vide")

    assert result["hits"] == []
    assert result["count"] == 0