# aria/memory/mempalace_writer.py

from datetime import datetime, timezone
from uuid import uuid4

from config import config
from mempalace.palace import get_collection


def store_interaction(
    text: str,
    intent_id: str,
    metadata: dict | None = None,
):
    col = get_collection(config.mempalace_path)

    doc_id = f"interaction_{intent_id}_{uuid4().hex[:8]}"

    col.upsert(
        documents=[text],
        ids=[doc_id],
        metadatas=[{
            "wing": "aria",
            "room": intent_id,
            "intent": intent_id,
            "type": "interaction",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **(metadata or {}),
        }],
    )