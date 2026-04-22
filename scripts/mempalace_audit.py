from chromadb import PersistentClient
from collections import Counter
import json


MEMPALACE_PATH = "/home/nico/.mempalace/palace"
COLLECTION_NAME = "mempalace_drawers"


def load_collection():
    client = PersistentClient(path=MEMPALACE_PATH)
    return client.get_collection(COLLECTION_NAME)


def audit_basic_stats(col):
    data = col.get()

    print("\n=== BASIC STATS ===")
    print("TOTAL ENTRIES:", len(data["ids"]))

    wings = Counter()
    rooms = Counter()

    for meta in data["metadatas"]:
        wings[meta.get("wing", "MISSING")] += 1
        rooms[meta.get("room", "MISSING")] += 1

    print("\n=== WINGS ===")
    for k, v in wings.most_common():
        print(k, v)

    print("\n=== ROOMS ===")
    for k, v in rooms.most_common(20):
        print(k, v)


def audit_missing_fields(col):
    data = col.get()

    required = {"wing", "room", "hall"}
    missing = Counter()

    for meta in data["metadatas"]:
        for k in required:
            if k not in meta:
                missing[k] += 1

    print("\n=== MISSING FIELDS ===")
    for k, v in missing.items():
        print(k, v)


def detect_schema_anomalies(col):
    data = col.get()

    uuid_like_rooms = 0
    cache_like = 0

    for meta in data["metadatas"]:
        room = meta.get("room", "")

        if isinstance(room, str):
            if len(room) > 10 and room[0].isalnum() and "-" in room:
                uuid_like_rooms += 1

            if "cache" in room or "classifier" in room:
                cache_like += 1

    print("\n=== ANOMALIES ===")
    print("UUID_LIKE_ROOMS:", uuid_like_rooms)
    print("CACHE_LIKE:", cache_like)


def sample_meta(col, n=5):
    data = col.get()

    print("\n=== SAMPLES ===")

    for meta in data["metadatas"][:n]:
        print(json.dumps({
            "wing": meta.get("wing"),
            "room": meta.get("room"),
            "keys": list(meta.keys())
        }, indent=2))


def main():
    col = load_collection()

    audit_basic_stats(col)
    audit_missing_fields(col)
    detect_schema_anomalies(col)
    sample_meta(col)


if __name__ == "__main__":
    main()