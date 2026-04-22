# tests/test_mempalace_bridge_intent.py

from memory.mempalace_bridge import retrieve_by_intent


def test_retrieve_by_intent_basic():
    res = retrieve_by_intent(
        query="test query",
        intent_id="test_intent_123"
    )

    assert isinstance(res, dict)
    assert "hits" in res
    assert "count" in res
    assert res["count"] == len(res["hits"])