# tests/test_mempalace_writer.py

from memory.mempalace_writer import store_interaction


def test_store_interaction_basic():
    # smoke test uniquement (pas d'assert sur DB ici)
    store_interaction(
        text="hello world",
        intent_id="test_intent",
        metadata={"source": "unit_test"}
    )