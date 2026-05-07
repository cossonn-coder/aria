# scripts/count_memory_by_wing.py
#
# Outil de diagnostic récurrent : répartition des entrées mémoire par wing.
# Utile pour surveiller les déséquilibres et détecter des écritures parasites.
#
# Usage : ./venv/bin/python scripts/count_memory_by_wing.py

import chromadb
from collections import Counter

PALACE_PATH = "/home/nico/.mempalace/palace"
COLLECTIONS = ["mempalace_drawers", "mempalace_closets"]


def count_by_wing(col) -> dict:
    result = col.get(include=["metadatas"])
    counter = Counter()
    for meta in result["metadatas"]:
        wing = meta.get("wing", "<no_wing>") if meta else "<no_wing>"
        counter[wing] += 1
    return counter


def main():
    client = chromadb.PersistentClient(path=PALACE_PATH)

    for col_name in COLLECTIONS:
        try:
            col = client.get_collection(col_name)
        except Exception:
            print(f"{col_name}: collection introuvable")
            continue

        total = col.count()
        wings = count_by_wing(col)
        sorted_wings = dict(sorted(wings.items(), key=lambda x: x[1], reverse=True))
        print(f"{col_name}: total={total}, wings={sorted_wings}")


if __name__ == "__main__":
    main()
