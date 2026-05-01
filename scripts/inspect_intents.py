#!/usr/bin/env python3
# scripts/inspect_intents.py — inventaire lecture seule de ~/.aria/intents.json

import json
from pathlib import Path
from collections import Counter

STORE_PATH = Path.home() / ".aria" / "intents.json"

SUSPECT_TOKENS = [
    "système", "systeme", "instruction", "aucun", "vide", "parsing",
    "debug", "mode", "variables", "cot", "tableau", "sujet inexistant",
    "rien", "message", "traiter", "raisonnement", "format", "réponse",
    "liste vide", "liste d'", "résumé", "résume", "exemple", "voici",
    "json", "étape", "note :", "note:", "prompt",
]

SEP  = "─" * 72
SEP2 = "═" * 72

data = json.loads(STORE_PATH.read_text())
intents = list(data.values())

def is_suspect(name: str) -> bool:
    n = name.lower()
    return any(t in n for t in SUSPECT_TOKENS)

def activity(intent: dict) -> int:
    return len(intent.get("actions_history") or [])

# ── Comptages ─────────────────────────────────────────────────────────────────

by_status   = Counter(i.get("status", "?") for i in intents)
suspects    = [i for i in intents if is_suspect(i["name"])]
legit       = [i for i in intents if not is_suspect(i["name"])]

print(f"\n{SEP2}")
print(f"  INVENTAIRE DES INTENTS — {STORE_PATH}")
print(SEP2)
print(f"\n  Total : {len(intents)} intents\n")

print("  Par status :")
for status, count in by_status.most_common():
    print(f"    {status:12s} {count}")

print(f"\n  Suspects  : {len(suspects)}")
print(f"  Légitimes : {len(legit)}")

# ── Intents légitimes ─────────────────────────────────────────────────────────

print(f"\n{SEP}")
print("  INTENTS LÉGITIMES")
print(SEP)
legit_sorted = sorted(legit, key=lambda i: (-activity(i), i.get("status","?")))
for i in legit_sorted:
    act = activity(i)
    print(f"  [{i.get('status','?'):10s}]  activité={act:3d}  {i['name']!r}")

# ── Intents suspects ──────────────────────────────────────────────────────────

print(f"\n{SEP}")
print("  INTENTS SUSPECTS (noms artefacts)")
print(SEP)
suspects_sorted = sorted(suspects, key=lambda i: (-activity(i), i.get("status","?")))
for i in suspects_sorted:
    act = activity(i)
    last = (i.get("actions_history") or ["—"])[-1]
    last_excerpt = last[:60] + ("…" if len(last) > 60 else "")
    print(f"  [{i.get('status','?'):10s}]  activité={act:3d}  {i['name']!r}")
    print(f"               dernière action : {last_excerpt!r}")

print(f"\n{SEP2}\n")
