import sys, json
sys.path.insert(0, ".")
from memory.mempalace_bridge import MempalaceBridge
from embedding.embedder import get_embedder
from pathlib import Path

embedder = get_embedder()
bridge = MempalaceBridge(embedder=embedder)
res = bridge.retrieve_memories("vols pour Paris", n=10)

print("=== TOUS LES HITS ===")
for h in res.get("hits", []):
    print(f"  room={h.get('room')!r:50}  dist={h.get('distance', 'n/a')}")

rooms = [h.get("room") for h in res.get("hits", [])]
uuids = [r for r in rooms if r and len(r) == 36 and "-" in r]
print(f"\n=== {len(uuids)} UUIDs ===")

intents_path = Path.home() / ".aria" / "intents.json"
intents = json.loads(intents_path.read_text())
intent_ids = set(intents.keys()) if isinstance(intents, dict) else {i["id"] for i in intents}

for u in uuids:
    match = "✓ MATCH intents.json" if u in intent_ids else "✗ orphan (pas d'intent correspondant)"
    # retrouver le nom de l'intent
    if isinstance(intents, dict):
        name = intents.get(u, {}).get("name", "???")
    else:
        name = next((i.get("name", "???") for i in intents if i.get("id") == u), "???")
    print(f"  {u}  →  {match}  [{name}]")