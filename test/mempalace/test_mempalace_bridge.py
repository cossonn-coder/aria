# tests/test_mempalace_bridge.py

from memory.mempalace_bridge import retrieve_memories, retrieve_by_intent


def test_retrieve_memories_basic():
    res = retrieve_memories("test query", n=5)

    assert isinstance(res, dict)
    assert "hits" in res
    assert "count" in res
    assert res["count"] == len(res["hits"])


def test_retrieve_memories_zero_n():
    res = retrieve_memories("test query", n=0)

    assert res["hits"] == []
    assert res["count"] == 0