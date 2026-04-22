ALLOWED_HALLS = {
    "technical",
    "creative",
    "identity",
    "memory",
    "emotions",
    "consciousness",
    "family",
    "general"
}

from chromadb import PersistentClient

client = PersistentClient(path="/home/nico/.mempalace/palace")
col = client.get_collection("mempalace_drawers")

data = col.get()

updated = 0

for i, meta in enumerate(data["metadatas"]):

    hall = meta.get("hall", "general")

    if hall not in ALLOWED_HALLS:
        meta["hall"] = "general"

        col.update(
            ids=[data["ids"][i]],
            metadatas=[meta],
        )

        updated += 1

print("FIXED HALL:", updated)