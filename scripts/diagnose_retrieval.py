#!/usr/bin/env python3
# scripts/diagnose_retrieval.py — diagnostic retrieval mémoire, lecture seule

import sys, os, json, inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from pathlib import Path
from collections import Counter
from memory.mempalace_store import search
from memory.mempalace_bridge import MempalaceBridge
from config import config

SEP  = "─" * 72
SEP2 = "═" * 72

bridge = MempalaceBridge(store=search)

# ── Chargement des intents ────────────────────────────────────────────────────

intents_raw = json.loads((Path.home() / ".aria" / "intents.json").read_text())
intents_by_name = {v["name"]: v for v in intents_raw.values()}
intents_by_activity = sorted(intents_raw.values(),
                              key=lambda i: -len(i.get("actions_history") or []))

# ── 1. retrieve_memories — 3 queries ─────────────────────────────────────────

print(f"\n{SEP2}")
print("  1. retrieve_memories (épisodique global, sans filtre room)")
print(SEP2)

QUERIES = [
    "Pourquoi elle ne germent pas",
    "carottes germination",
    "j'avais commencé une liste de courses",
]

for q in QUERIES:
    result = bridge.retrieve_memories(q, n=8)
    hits = result.get("hits", [])
    print(f"\n  query: {q!r}")
    print(f"  → {len(hits)} hit(s)")
    print(f"  {SEP}")
    if not hits:
        print("    (aucun résultat)")
    for h in hits:
        text    = h.get("text", "")
        excerpt = (text[:100] + "…") if len(text) > 100 else text
        dist    = round(h.get("distance", -1), 4)
        room    = h.get("room", "?")
        wing    = h.get("wing", "?")
        typ     = h.get("type", "?")
        print(f"    dist={dist}  wing={wing}  room={room}  type={typ}")
        print(f"    {excerpt!r}")

# ── 2. retrieve_by_intent — recall ciblé ─────────────────────────────────────

print(f"\n{SEP2}")
print("  2. retrieve_by_intent (recall ciblé par intent_id)")
print(SEP2)

INTENT_QUERIES = [
    ("germination", "carottes dans jardin"),
    ("liste",       "liste de courses"),
]

for query, intent_name in INTENT_QUERIES:
    intent = intents_by_name.get(intent_name)
    if not intent:
        print(f"\n  ⚠  Intent {intent_name!r} introuvable dans intents.json")
        continue
    intent_id = intent["id"]
    result = bridge.retrieve_by_intent(query=query, intent_id=intent_id)
    hits = result.get("hits", [])
    print(f"\n  intent: {intent_name!r}  id={intent_id}")
    print(f"  query:  {query!r}")
    print(f"  → {len(hits)} hit(s)")
    print(f"  {SEP}")
    if not hits:
        print("    (aucun résultat)")
    for h in hits:
        text    = h.get("text", "")
        excerpt = (text[:100] + "…") if len(text) > 100 else text
        dist    = round(h.get("distance", -1), 4)
        room    = h.get("room", "?")
        print(f"    dist={dist}  room={room}")
        print(f"    {excerpt!r}")

# ── 3. Code source de retrieve_memories ──────────────────────────────────────

print(f"\n{SEP2}")
print("  3. Code source MempalaceBridge.retrieve_memories")
print(SEP2)
print(inspect.getsource(bridge.retrieve_memories))

# ── 4. Comptage des entrées par intent_id dans aria_episodic ─────────────────

print(f"\n{SEP2}")
print("  4. Entrées aria_episodic par room=intent_id (top 3 intents actifs)")
print(SEP2)

client = chromadb.PersistentClient(path=config.mempalace_path)
col = client.get_collection("mempalace_drawers")
data = col.get(include=["metadatas"])

episodic_by_room = Counter(
    m.get("room", "?")
    for m in data["metadatas"]
    if m.get("wing") == "aria_episodic"
)

top3 = intents_by_activity[:3]
print(f"\n  {'Intent':30s}  {'intent_id':36s}  entrées_episodic")
print(f"  {SEP}")
for intent in top3:
    name      = intent["name"]
    iid       = intent["id"]
    nb        = episodic_by_room.get(iid, 0)
    print(f"  {name:30s}  {iid}  {nb}")

# Vue d'ensemble des rooms les plus peuplées dans aria_episodic
print(f"\n  Top 15 rooms dans aria_episodic :")
print(f"  {SEP}")
for room, count in episodic_by_room.most_common(15):
    # Résoudre le nom d'intent si possible
    intent_name = next((v["name"] for v in intents_raw.values() if v["id"] == room), "—")
    print(f"  {count:4d}  room={room}  intent={intent_name!r}")

print(f"\n{SEP2}\n")
