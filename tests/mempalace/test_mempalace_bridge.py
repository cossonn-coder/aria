# tests/mempalace/test_mempalace_bridge.py
#
# Tests unitaires de MempalaceBridge — lecture mémoire épisodique.
#
# Stratégie :
#   MempalaceBridge est instancié avec un store fake (callable).
#   On ne patche plus memory.mempalace_bridge.search au niveau module —
#   le store est injecté directement au constructeur, ce qui est
#   plus propre et plus stable que le monkey-patching.

import pytest
from memory.mempalace_bridge import MempalaceBridge


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_bridge(results: list) -> MempalaceBridge:
    """Crée un bridge avec un store fake retournant les résultats fournis."""
    def fake_store(**kwargs):
        return {"results": results}
    return MempalaceBridge(store=fake_store)


def make_bridge_capturing() -> tuple[MempalaceBridge, list]:
    """
    Crée un bridge dont le store capture les kwargs de chaque appel.
    Utile pour vérifier que les bons paramètres sont transmis.
    """
    captured = []
    def fake_store(**kwargs):
        captured.append(kwargs)
        return {"results": []}
    return MempalaceBridge(store=fake_store), captured


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_retrieve_memories_basic():
    """Le résultat doit toujours contenir hits et count cohérents."""
    bridge = make_bridge([
        {"text": "souvenir A", "distance": 0.3, "room": "intent-001"},
        {"text": "souvenir B", "distance": 0.5, "room": "intent-001"},
    ])

    res = bridge.retrieve_memories("test query", n=5)

    assert isinstance(res, dict)
    assert "hits" in res
    assert "count" in res
    assert res["count"] == len(res["hits"])


def test_retrieve_memories_zero_n():
    """n=0 doit retourner vide sans appeler le store."""
    calls = []

    def fake_store(**kwargs):
        calls.append(kwargs)
        return {"results": []}

    bridge = MempalaceBridge(store=fake_store)
    res = bridge.retrieve_memories("test query", n=0)

    assert calls == [], "Le store ne doit pas être appelé pour n=0"
    assert res["hits"] == []
    assert res["count"] == 0


def test_retrieve_memories_type_filter():
    """type_filter doit retenir uniquement les hits du type demandé."""
    bridge = make_bridge([
        {"text": "img1", "room": "a", "distance": 0.2, "type": "image_generated"},
        {"text": "img2", "room": "a", "distance": 0.3, "type": "image_input"},
        {"text": "txt1", "room": "a", "distance": 0.1, "type": "interaction"},
    ])

    res = bridge.retrieve_memories(
        query="test",
        n=10,
        type_filter=["image_generated"],
    )

    assert res["count"] == 1
    assert res["hits"][0]["type"] == "image_generated"


def test_retrieve_memories_filters_distance():
    """Les hits avec distance >= 0.8 doivent être exclus."""
    bridge = make_bridge([
        {"text": "ok",      "distance": 0.5, "room": "r"},
        {"text": "trop loin", "distance": 0.9, "room": "r"},
    ])

    res = bridge.retrieve_memories("query", n=5)

    assert res["count"] == 1
    assert res["hits"][0]["text"] == "ok"


def test_retrieve_memories_filters_general_room():
    """Les hits de room='general' doivent être exclus."""
    bridge = make_bridge([
        {"text": "ciblé",    "distance": 0.3, "room": "intent-001"},
        {"text": "générique","distance": 0.3, "room": "general"},
    ])

    res = bridge.retrieve_memories("query", n=5)

    assert res["count"] == 1
    assert res["hits"][0]["text"] == "ciblé"