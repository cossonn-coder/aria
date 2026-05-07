#!/usr/bin/env python3
# scripts/wipe_classifier_cache.py
#
# Wipe complet de la wing aria_classifier (cache classifier).
#
# Contexte : les ~199 entrées historiques ont été écrites avec un schéma
# cassé (document = JSON, mismatch embedding cf. dette #20). Après le fix
# T2 sprint 5, le schéma change : document = message brut, operation
# portée par room. Une migration in-place serait coûteuse et sans
# bénéfice (entrées inertes — le cache ne hit jamais aujourd'hui).
# Le wipe permet de repartir d'un schéma propre, le pipeline normal
# repeuple incrémentalement.
#
# Usage :
#   python scripts/wipe_classifier_cache.py            # dry-run
#   python scripts/wipe_classifier_cache.py --execute  # exécution réelle

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from config import config

DRY_RUN = "--execute" not in sys.argv
PALACE_PATH = config.mempalace_path

SEP = "═" * 60

client = chromadb.PersistentClient(path=PALACE_PATH)
col = client.get_collection("mempalace_drawers")

# ── Comptage avant ───────────────────────────────────────────────────────────

before = col.get(where={"wing": "aria_classifier"}, include=[])
count_before = len(before["ids"])

print(f"\n{SEP}")
print("  WIPE wing=aria_classifier")
print(f"  Palace : {PALACE_PATH}")
print(f"  Mode   : {'DRY-RUN (aucune écriture)' if DRY_RUN else '*** EXÉCUTION RÉELLE ***'}")
print(f"{SEP}")
print(f"\n  BEFORE: {count_before} entries in wing=aria_classifier")

if DRY_RUN:
    print("\n  Dry-run terminé — aucune suppression effectuée.")
    print("  Relancer avec --execute pour appliquer le wipe.")
    print(f"\n{SEP}\n")
    sys.exit(0)

# ── Suppression ───────────────────────────────────────────────────────────────

col.delete(where={"wing": "aria_classifier"})

# ── Vérification ──────────────────────────────────────────────────────────────

after = col.get(where={"wing": "aria_classifier"}, include=[])
count_after = len(after["ids"])

print(f"  AFTER : {count_after} entries in wing=aria_classifier")

if count_after != 0:
    print(f"\n  ⚠  Wipe incomplet : {count_after} entrées résiduelles.")
    sys.exit(1)

print("\n  Wipe terminé proprement. Le pipeline normal repeuplera le cache.")
print(f"\n{SEP}\n")
