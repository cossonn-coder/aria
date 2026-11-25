# tests/memory/test_mempalace_bridge_feedback.py
#
# Sprint 67 : load_feedback lit les messages notés, filtrés par date et triés.

from memory.mempalace_bridge import MempalaceBridge


def test_load_feedback_filters_since_and_sorts():
    def fake_get_by_metadata(path, where, include=None):
        assert where == {"$and": [{"wing": "aria_feedback"}, {"type": "sent_message"}]}
        return {
            "ids": ["tg_42_3", "tg_42_1", "tg_42_2"],
            "documents": ["récent", "vieux réagi", "vieux"],
            "metadatas": [
                {"timestamp": "2026-11-25T10:00", "reaction": ""},
                {"timestamp": "2026-11-01T10:00", "reaction": "😢", "reacted_at": "2026-11-25T09:00"},
                {"timestamp": "2026-11-02T10:00", "reaction": ""},
            ],
        }

    bridge = MempalaceBridge(store=None, get_by_metadata=fake_get_by_metadata)

    feedback = bridge.load_feedback(since="2026-11-20")

    assert [f["id"] for f in feedback] == ["tg_42_1", "tg_42_3"]
    assert feedback[0]["text"] == "vieux réagi"
