#aria/intent/intent_store.py
import json
from pathlib import Path
from intent.intent import Intent, IntentStatus


STORE_PATH = Path.home() / ".aria" / "intents.json"


def save_intents(intents: dict[str, Intent]):
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    for intent_id, intent in intents.items():
        data[intent_id] = {
            "id": intent.id,
            "name": intent.name,
            "description": intent.description,
            "status": intent.status.value if hasattr(intent.status, 'value') else intent.status,
            "next_action": intent.next_action,
            "actions_history": intent.actions_history,
        }
    STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def load_intents(embedder) -> dict[str, Intent]:
    if not STORE_PATH.exists():
        return {}
    try:
        data = json.loads(STORE_PATH.read_text())
        intents = {}
        for intent_id, d in data.items():
            intent = Intent(
                id=d["id"],
                name=d.get("name") or d.get("subject") or "",
                description=d.get("description", ""),
                status=IntentStatus(d.get("status", "active")),
                next_action=d.get("next_action"),
                actions_history=d.get("actions_history", []),
            )
            intent.embedding = embedder.encode([intent.name])[0]
            intents[intent_id] = intent
        return intents
    except Exception as e:
        print(f"[INTENT STORE] load error: {e}")
        return {}