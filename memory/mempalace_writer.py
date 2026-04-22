# aria/memory/mempalace_writer.py

from datetime import datetime, timezone
from uuid import uuid4

from config import config
from mempalace.palace import get_collection


REQUIRED_FIELDS = {"wing", "room", "type", "intent"}


def validate(meta: dict):
    missing = REQUIRED_FIELDS - set(meta.keys())
    if missing:
        raise ValueError(f"MemPalace schema violation: missing {missing}")


def store_interaction(
    text: str,
    intent_id: str,
    user_id: str,
    metadata: dict | None = None,
):
    col = get_collection(config.mempalace_path)

    doc_id = f"interaction_{intent_id}_{uuid4().hex[:8]}"

    meta = {
        "wing": "aria",
        "room": intent_id,
        "intent": intent_id,
        "type": "interaction",
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **(metadata or {}),
    }

    validate(meta)

    col.upsert(
        documents=[text],
        ids=[doc_id],
        metadatas=[meta],
    )