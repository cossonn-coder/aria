#!/usr/bin/env python3
# scripts/clean_intents.py
#
# Suppression des intents artefacts de ~/.aria/intents.json.
#
# Usage :
#   python scripts/clean_intents.py             # dry-run (lecture seule)
#   python scripts/clean_intents.py --execute   # suppression réelle avec backup
#
# Les intents sont identifiés par NAME (lisible + auditable).
# Ne touche pas MemPalace — les entrées épisodiques orphelines restent intactes.

import json
import sys
import shutil
from datetime import datetime
from pathlib import Path

STORE_PATH = Path.home() / ".aria" / "intents.json"

# ── Intents à supprimer ───────────────────────────────────────────────────────
#
# 13 artefacts d'extraction LLM (nom = fragment de raisonnement ou message
# d'erreur de l'extracteur, jamais un vrai sujet utilisateur) :

NAMES_TO_DELETE = {
    # Extracteur qui retourne ses propres messages d'erreur
    "il n'y a pas de message à traiter",
    "aucun sujet fourni",
    "aucun message fourni",
    "aucun sujet",
    "sujet inexistant",
    "rien",

    # Fragments de réponses LLM au format markdown/XML/tableau
    "parsing et debug",
    "cot reasoning",
    "instruction système",
    "mode détecté",
    "tableau vide",
    "étape concise",
    "variables liste",

    # Borderline — noms génériques sans sujet utilisateur réel
    "sujet inconnu",
    "sujet principal manquant",
}

# ─────────────────────────────────────────────────────────────────────────────

DRY_RUN = "--execute" not in sys.argv
SEP  = "─" * 70
SEP2 = "═" * 70

data = json.loads(STORE_PATH.read_text())

to_delete = {k: v for k, v in data.items() if v.get("name", "") in NAMES_TO_DELETE}
to_keep   = {k: v for k, v in data.items() if v.get("name", "") not in NAMES_TO_DELETE}

# Noms demandés mais absents du fichier (pour détecter les dérives de nommage)
found_names   = {v["name"] for v in to_delete.values()}
missing_names = NAMES_TO_DELETE - found_names

print(f"\n{SEP2}")
print("  NETTOYAGE DES INTENTS ARTEFACTS")
print(f"  Fichier : {STORE_PATH}")
print(f"  Mode    : {'DRY-RUN (aucune écriture)' if DRY_RUN else '*** EXÉCUTION RÉELLE ***'}")
print(SEP2)

print(f"\n  Avant  : {len(data)} intents")
print(f"  À supprimer : {len(to_delete)}")
print(f"  À conserver : {len(to_keep)}")

print(f"\n{SEP}")
print("  INTENTS SUPPRIMÉS")
print(SEP)
for intent in sorted(to_delete.values(), key=lambda i: -len(i.get("actions_history") or [])):
    nb = len(intent.get("actions_history") or [])
    print(f"  ✗  [{intent.get('status','?'):10s}]  actions={nb:3d}  id={intent['id']}")
    print(f"     nom : {intent['name']!r}")

if missing_names:
    print(f"\n  ⚠  Noms demandés mais absents du fichier :")
    for n in sorted(missing_names):
        print(f"     - {n!r}")

print(f"\n{SEP}")
print("  INTENTS CONSERVÉS")
print(SEP)
for intent in sorted(to_keep.values(), key=lambda i: -len(i.get("actions_history") or [])):
    nb = len(intent.get("actions_history") or [])
    print(f"  ✓  [{intent.get('status','?'):10s}]  actions={nb:3d}  {intent['name']!r}")

if DRY_RUN:
    print(f"\n{SEP}")
    print("  Dry-run terminé — aucune modification effectuée.")
    print("  Relancer avec --execute pour appliquer.")
    print(f"{SEP}\n")
    sys.exit(0)

# ── Backup ────────────────────────────────────────────────────────────────────

ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup_path = STORE_PATH.with_suffix(f".json.backup.{ts}")
shutil.copy2(STORE_PATH, backup_path)
print(f"\n  Backup : {backup_path}")

# ── Écriture atomique ─────────────────────────────────────────────────────────

tmp_path = STORE_PATH.with_suffix(".json.tmp")
tmp_path.write_text(json.dumps(to_keep, ensure_ascii=False, indent=2))
tmp_path.replace(STORE_PATH)

print(f"  Après  : {len(to_keep)} intents")
print(f"\n{SEP}")
print(f"  Terminé — {len(to_delete)} intents supprimés, {len(to_keep)} conservés.")
print(f"{SEP}\n")
