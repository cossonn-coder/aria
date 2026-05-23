# tests/memory/test_mempalace_bridge.py
#
# Tests unitaires de MempalaceBridge.load_conversation_history.
#
# Stratégie :
#   Le bridge est instancié avec un get_by_metadata fake (callable)
#   qui retourne un dict natif ChromaDB préfabriqué
#   {documents, metadatas}. Pas d'accès palace réel, pas de ChromaDB.
#
# Note : un second fichier tests/mempalace/test_mempalace_bridge.py
# couvre déjà retrieve_memories / retrieve_by_intent / retrieve_semantic.
# Ce fichier-ci est strictement dédié à load_conversation_history
# (sprint 15).

import pytest

from memory.mempalace_bridge import MempalaceBridge


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_get(payload: dict):
    """Construit un get_by_metadata fake qui retourne payload tel quel."""
    captured = []

    def fake_get(palace_path, where, include=None):
        captured.append({"palace_path": palace_path, "where": where, "include": include})
        return payload

    return fake_get, captured


def _payload(turns: list[tuple[str, str, str]]) -> dict:
    """Construit un dict natif ChromaDB à partir d'une liste
    [(role, content, timestamp_iso), ...]."""
    return {
        "documents": [content for _, content, _ in turns],
        "metadatas": [{"role": role, "timestamp": ts} for role, _, ts in turns],
    }


# ── 1. load_history empty conversation → liste vide ──────────────────────────

def test_load_history_empty_returns_empty_list():
    fake_get, _ = _make_get({"documents": [], "metadatas": []})
    bridge = MempalaceBridge(store=lambda **kw: {}, get_by_metadata=fake_get)

    out = bridge.load_conversation_history("conv-unknown", n=10)

    assert out == []


# ── 2. load_history → ordre chronologique croissant ──────────────────────────

def test_load_history_returns_chronological_order():
    """Insertion en désordre, lecture doit trier par timestamp croissant."""
    payload = _payload([
        ("assistant", "réponse 2", "2026-05-23T12:00:02+00:00"),
        ("user", "msg 1", "2026-05-23T12:00:00+00:00"),
        ("user", "msg 2", "2026-05-23T12:00:01+00:00"),
    ])
    fake_get, _ = _make_get(payload)
    bridge = MempalaceBridge(store=lambda **kw: {}, get_by_metadata=fake_get)

    out = bridge.load_conversation_history("conv-1", n=10)

    contents = [t["content"] for t in out]
    assert contents == ["msg 1", "msg 2", "réponse 2"]


# ── 3. load_history caps at n — retourne les n plus RÉCENTS ──────────────────

def test_load_history_caps_at_n():
    """5 turns, n=3 → on garde les 3 plus récents (par timestamp)."""
    payload = _payload([
        ("user", "t1", "2026-05-23T12:00:00+00:00"),
        ("assistant", "t2", "2026-05-23T12:00:01+00:00"),
        ("user", "t3", "2026-05-23T12:00:02+00:00"),
        ("assistant", "t4", "2026-05-23T12:00:03+00:00"),
        ("user", "t5", "2026-05-23T12:00:04+00:00"),
    ])
    fake_get, _ = _make_get(payload)
    bridge = MempalaceBridge(store=lambda **kw: {}, get_by_metadata=fake_get)

    out = bridge.load_conversation_history("conv-1", n=3)

    contents = [t["content"] for t in out]
    assert contents == ["t3", "t4", "t5"]


# ── 4. load_history n > available → retourne tout ────────────────────────────

def test_load_history_n_greater_than_available_returns_all():
    payload = _payload([
        ("user", "a", "2026-05-23T12:00:00+00:00"),
        ("assistant", "b", "2026-05-23T12:00:01+00:00"),
    ])
    fake_get, _ = _make_get(payload)
    bridge = MempalaceBridge(store=lambda **kw: {}, get_by_metadata=fake_get)

    out = bridge.load_conversation_history("conv-1", n=100)

    contents = [t["content"] for t in out]
    assert contents == ["a", "b"]


# ── 5. load_history isole les conversations distinctes ───────────────────────

def test_load_history_isolates_distinct_conversations():
    """L'isolation est portée par le filtre where transmis à
    get_by_metadata. Le fake n'a qu'à vérifier que conv "B" reçoit
    bien un where pointant sur "B" — et que ce qu'on lui retourne
    pour "B" n'est PAS ce qu'on a stocké pour "A"."""
    payload_a = _payload([("user", "msg A", "2026-05-23T12:00:00+00:00")])
    payload_b = _payload([("user", "msg B", "2026-05-23T12:00:00+00:00")])

    def fake_get(palace_path, where, include=None):
        # On extrait la valeur de room depuis le where {$and: [{wing:...}, {room:...}]}
        clauses = where.get("$and", [])
        room = next((c["room"] for c in clauses if "room" in c), None)
        return payload_a if room == "A" else payload_b

    bridge = MempalaceBridge(store=lambda **kw: {}, get_by_metadata=fake_get)

    out_a = bridge.load_conversation_history("A", n=10)
    out_b = bridge.load_conversation_history("B", n=10)

    assert [t["content"] for t in out_a] == ["msg A"]
    assert [t["content"] for t in out_b] == ["msg B"]


# ── 6. load_history sans get_by_metadata injecté → RuntimeError ──────────────

def test_load_history_raises_if_get_by_metadata_not_injected():
    """Le bridge construit sans get_by_metadata reste valide pour les
    autres méthodes (retrieve_*), mais load_conversation_history doit
    lever RuntimeError explicite plutôt qu'AttributeError silencieux."""
    bridge = MempalaceBridge(store=lambda **kw: {})

    with pytest.raises(RuntimeError, match="get_by_metadata"):
        bridge.load_conversation_history("conv-1", n=10)
