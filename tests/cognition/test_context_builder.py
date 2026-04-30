# tests/cognition/test_context_builder.py
#
# Tests unitaires du ContextBuilder.
#
# bridge est mocké — aucun ChromaDB nécessaire.
# La fonction est stateless mais pas pure (appel I/O via bridge).

import math
from unittest.mock import MagicMock
import pytest

from cognition.context_builder import build_context_block, _estimate_tokens
from memory.mempalace_bridge import MempalaceBridge


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_bridge(semantic_hits=None):
    bridge = MagicMock(spec=MempalaceBridge)
    bridge.retrieve_semantic.return_value = {
        "hits": semantic_hits or [],
        "count": len(semantic_hits or []),
    }
    return bridge


def make_intent(name: str, salience: float):
    intent = MagicMock()
    intent.name = name
    intent.salience = salience
    return intent


def make_hit(text: str, distance: float = 0.3):
    return {"text": text, "distance": distance}


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_empty_all():
    bridge = make_bridge()
    result = build_context_block("query", bridge, [], {"hits": []})
    assert result == ""


def test_semantic_section_present():
    bridge = make_bridge([make_hit("Nico est allergique au gluten")])
    result = build_context_block("gluten", bridge, [], {"hits": []})
    assert "[Profil utilisateur stable]" in result
    assert "allergique au gluten" in result


def test_semantic_section_absent_when_no_hits():
    bridge = make_bridge([])
    result = build_context_block("query", bridge, [], {"hits": []})
    assert "[Profil utilisateur stable]" not in result


def test_intents_sorted_by_salience():
    bridge = make_bridge()
    intents = [make_intent("Faible", 0.3), make_intent("Haute", 0.9)]
    result = build_context_block("query", bridge, intents, {"hits": []})
    assert "[Projets actifs]" in result
    assert result.index("Haute") < result.index("Faible")


def test_memories_sorted_by_distance():
    bridge = make_bridge()
    hits = [make_hit("distant", 0.7), make_hit("proche", 0.1)]
    result = build_context_block("query", bridge, [], {"hits": hits})
    assert "[Souvenirs pertinents]" in result
    assert result.index("proche") < result.index("distant")


def test_token_budget_respected():
    big_hits = [make_hit("x" * 400) for _ in range(20)]
    bridge = make_bridge(big_hits)
    intents = [make_intent(f"project_{i}", float(i)) for i in range(20)]
    episodic = [make_hit("y" * 400, 0.01 * i) for i in range(20)]
    result = build_context_block(
        "query", bridge, intents, {"hits": episodic}, token_budget=500
    )
    assert math.ceil(len(result) / 4) <= 500


def test_truncation_keeps_best_items():
    bridge = make_bridge()
    intents = [make_intent("PrioriteHaute", 0.99), make_intent("PrioriteBasse", 0.1)]
    result = build_context_block("q", bridge, intents, {"hits": []}, token_budget=50)
    if "[Projets actifs]" in result:
        assert "PrioriteHaute" in result


def test_no_intents_section_when_empty():
    bridge = make_bridge()
    result = build_context_block("q", bridge, [], {"hits": []})
    assert "[Projets actifs]" not in result


def test_no_episodic_section_when_empty():
    bridge = make_bridge()
    result = build_context_block("q", bridge, [], {"hits": []})
    assert "[Souvenirs pertinents]" not in result


def test_semantic_called_with_query():
    bridge = make_bridge()
    build_context_block("ma requête", bridge, [], {"hits": []})
    bridge.retrieve_semantic.assert_called_once_with("ma requête", n=5)
