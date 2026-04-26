# tests/test_mempalace_bridge.py

import pytest
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

def test_retrieve_memories_type_filter(monkeypatch):

    fake_data = {
        "results": [
            {
                "text": "img1",
                "room": "a",
                "distance": 0.2,
                "type": "image_generated",
            },
            {
                "text": "img2",
                "room": "a",
                "distance": 0.3,
                "type": "image_input",
            },
            {
                "text": "txt1",
                "room": "a",
                "distance": 0.1,
                "type": "text",
            },
        ]
    }

    def fake_search(*args, **kwargs):
        return fake_data

    monkeypatch.setattr(
        "memory.mempalace_bridge.search",
        fake_search
    )

    res = retrieve_memories(
        query="test",
        n=10,
        type_filter=["image_generated"]
    )

    assert res["count"] == 1
    assert res["hits"][0]["type"] == "image_generated"