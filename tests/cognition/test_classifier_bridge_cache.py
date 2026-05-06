# tests/cognition/test_classifier_bridge_cache.py
#
# Garde-fou R5 : classify_operation doit passer par MempalaceBridge
# pour le cache classifier, sans importer mempalace_store directement.

import json
from unittest.mock import MagicMock

from cognition.cognitive_classifier import classify_operation
from cognition.cognitive_context import CognitiveOperation


def _make_bridge(similarity: float, operation: str = "fact_recall") -> MagicMock:
    bridge = MagicMock()
    bridge.retrieve_memories.return_value = {
        "hits": [{
            "similarity": similarity,
            "text": json.dumps({"message": "test", "operation": operation}),
        }]
    }
    return bridge


def test_classify_operation_uses_bridge_cache():
    """Si le bridge retourne un hit à similarity>=0.92, le LLM est court-circuité."""
    bridge = _make_bridge(similarity=0.95)

    result = classify_operation(
        message="quelles graines n'ont pas germé ?",
        llm_router=None,
        bridge=bridge,
    )

    assert result == CognitiveOperation.FACT_RECALL
    bridge.retrieve_memories.assert_called_once_with(
        query="quelles graines n'ont pas germé ?",
        wing="aria_classifier",
        n=1,
    )


def test_classify_operation_skips_cache_below_threshold():
    """Un hit à similarity<0.92 est ignoré — pas de cache hit."""
    bridge = _make_bridge(similarity=0.85)

    result = classify_operation(
        message="quelles graines n'ont pas germé ?",
        llm_router=None,
        bridge=bridge,
    )

    # Sous le seuil + pas de LLM → UNKNOWN
    assert result == CognitiveOperation.UNKNOWN
    bridge.retrieve_memories.assert_called_once()


def test_classify_operation_no_bridge_skips_cache():
    """Sans bridge, le cache est ignoré silencieusement."""
    result = classify_operation(
        message="quelles graines n'ont pas germé ?",
        llm_router=None,
        bridge=None,
    )
    assert result == CognitiveOperation.UNKNOWN


def test_classify_operation_bridge_empty_hits():
    """Bridge disponible mais aucun résultat → pas de cache hit."""
    bridge = MagicMock()
    bridge.retrieve_memories.return_value = {"hits": []}

    result = classify_operation(
        message="quelles graines n'ont pas germé ?",
        llm_router=None,
        bridge=bridge,
    )
    assert result == CognitiveOperation.UNKNOWN
