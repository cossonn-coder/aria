import json

import intent.intent_store as intent_store
from intent.intent import Intent


def test_save_intents_truncates_long_actions():
    # Une action longue (bloc enrichi) est coupée à 100 car. sur disque, la courte reste intacte.
    intent = Intent(name="jeux echecs", actions_history=["x" * 9000, "courte"])

    intent_store.save_intents({intent.id: intent})

    data = json.loads(intent_store.STORE_PATH.read_text())
    history = data[intent.id]["actions_history"]
    assert len(history) == 2
    assert history[0] == "x" * 100
    assert history[1] == "courte"
    # L'objet en mémoire n'est pas modifié.
    assert len(intent.actions_history[0]) == 9000
