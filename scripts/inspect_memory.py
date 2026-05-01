#!/usr/bin/env python3
# scripts/inspect_memory.py — diagnostic lecture seule de MemPalace
# Usage : python scripts/inspect_memory.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from config import config
from memory.mempalace_store import search
from memory.mempalace_bridge import MempalaceBridge

PALACE_PATH = config.mempalace_path
SEP = "─" * 60

bridge = MempalaceBridge(store=search)


# ══════════════════════════════════════════════════════════════
# 1. INVENTAIRE DES WINGS (collections ChromaDB)
# ══════════════════════════════════════════════════════════════

print(f"\n{'═'*60}")
print("  INVENTAIRE DES WINGS — MemPalace")
print(f"  Palace path : {PALACE_PATH}")
print(f"{'═'*60}")

client = chromadb.PersistentClient(path=PALACE_PATH)
collections = client.list_collections()

if not collections:
    print("  ⚠  Aucune collection trouvée dans MemPalace.")
else:
    for col in sorted(collections, key=lambda c: c.name):
        count = col.count()
        print(f"\n  Wing : {col.name}  ({count} entrées)")
        print(f"  {SEP}")

        # 3 entrées exemples
        sample = col.get(limit=3, include=["documents", "metadatas"])
        docs = sample.get("documents") or []
        metas = sample.get("metadatas") or []
        ids = sample.get("ids") or []

        if not docs:
            print("    (aucune entrée)")
        for i, (doc, meta, eid) in enumerate(zip(docs, metas, ids), 1):
            excerpt = (doc[:120] + "…") if doc and len(doc) > 120 else (doc or "")
            wing_m = meta.get("wing", "?") if meta else "?"
            room_m = meta.get("room", "?") if meta else "?"
            typ_m  = meta.get("type", "?") if meta else "?"
            print(f"    [{i}] id     : {eid}")
            print(f"        wing   : {wing_m} / room : {room_m} / type : {typ_m}")
            print(f"        texte  : {excerpt}")


# ══════════════════════════════════════════════════════════════
# 2. TESTS DE REQUÊTES VIA BRIDGE
# ══════════════════════════════════════════════════════════════

def show_results(label: str, result: dict):
    hits = result.get("hits", [])
    print(f"\n  {label}")
    print(f"  {SEP}")
    print(f"  → {len(hits)} hit(s)")
    if not hits:
        print("    (aucun résultat)")
        return
    for i, h in enumerate(hits, 1):
        text  = h.get("text", "")
        excerpt = (text[:120] + "…") if len(text) > 120 else text
        dist  = round(h.get("distance", -1), 4)
        wing  = h.get("wing",  h.get("metadata", {}).get("wing",  "?"))
        room  = h.get("room",  h.get("metadata", {}).get("room",  "?"))
        typ   = h.get("type",  h.get("metadata", {}).get("type",  "?"))
        print(f"    [{i}] dist={dist}  wing={wing}  room={room}  type={typ}")
        print(f"         {excerpt}")


print(f"\n\n{'═'*60}")
print("  TESTS retrieve_memories (épisodique)")
print(f"{'═'*60}")

queries_episodic = [
    "carottes",
    "gluten",
    "liste de courses",
]
for q in queries_episodic:
    show_results(f'retrieve_memories("{q}", n=5)', bridge.retrieve_memories(q, n=5))


print(f"\n\n{'═'*60}")
print("  TESTS retrieve_semantic (faits stables)")
print(f"{'═'*60}")

queries_semantic = [
    "allergie",
    "gluten",
]
for q in queries_semantic:
    show_results(f'retrieve_semantic("{q}", n=5)', bridge.retrieve_semantic(q, n=5))

print(f"\n{'═'*60}\n")
