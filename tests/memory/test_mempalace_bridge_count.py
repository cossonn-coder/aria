# tests/memory/test_mempalace_bridge_count.py
#
# Sprint 40 (#131) : count_by_wing pour /status.

from memory.mempalace_bridge import MempalaceBridge


def test_count_by_wing_one_query_per_wing():
    calls = []

    def fake_get_by_metadata(path, where, include=None):
        calls.append((where, include))
        n = {"aria_episodic": 3, "aria_conversation": 2}.get(where["wing"], 0)
        return {"ids": [f"id{i}" for i in range(n)]}

    bridge = MempalaceBridge(store=None, get_by_metadata=fake_get_by_metadata)

    assert bridge.count_by_wing() == {
        "aria_episodic": 3,
        "aria_semantic": 0,
        "aria_classifier": 0,
        "aria_conversation": 2,
    }
    assert all(include == [] for _, include in calls)
