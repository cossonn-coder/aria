# scripts/mempalace_normalize.py

from chromadb import PersistentClient

client = PersistentClient(path="/home/nico/.mempalace/palace")
col = client.get_collection("mempalace_drawers")

data = col.get()

updated = 0

for i, meta in enumerate(data["metadatas"]):

    new_meta = dict(meta)

    # 1. type obligatoire
    if "type" not in new_meta:
        new_meta["type"] = "unknown"

    # 2. hall obligatoire
    if "hall" not in new_meta:
        new_meta["hall"] = "legacy"

    # 3. room cleanup (UUID noise)
    room = new_meta.get("room", "")

    if isinstance(room, str) and len(room) > 20 and "-" in room:
        new_meta["room"] = "legacy_room"

    # 4. wing safety
    if new_meta.get("wing") not in ["aria", "aria_classifier"]:
        new_meta["wing"] = "aria"

    col.update(
        ids=[data["ids"][i]],
        metadatas=[new_meta],
    )

    updated += 1

print("UPDATED:", updated)