#!/usr/bin/env python3
# scripts/migrate_wing_aria_to_episodic.py
#
# Migration : wing="aria" → wing="aria_episodic" dans mempalace_drawers.
#
# Contexte : les entrées historiques ont été écrites avec wing="aria"
# (ancien format). Le bridge lit maintenant wing="aria_episodic".
# Cette migration aligne les métadonnées sur la convention courante.
#
# Périmètre :
#   - Migre UNIQUEMENT les entrées avec wing="aria"
#   - Ne touche PAS wing="aria_classifier" (cache classifieur)
#   - Ne touche PAS wing="aria_episodic" (déjà correct)
#   - Ne modifie pas les documents, ids, embeddings — uniquement la métadonnée wing
#
# Usage :
#   python scripts/migrate_wing_aria_to_episodic.py           # dry-run
#   python scripts/migrate_wing_aria_to_episodic.py --execute # migration réelle

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chromadb
from collections import Counter
from config import config

DRY_RUN = "--execute" not in sys.argv
PALACE_PATH = config.mempalace_path
BATCH_SIZE = 100

SEP = "─" * 60

client = chromadb.PersistentClient(path=PALACE_PATH)
col = client.get_collection("mempalace_drawers")

# ── Lecture complète ─────────────────────────────────────────────────────────

data = col.get(include=["metadatas", "documents"])
all_ids   = data["ids"]
all_metas = data["metadatas"]

# ── Sélection des candidats à migrer ─────────────────────────────────────────

candidates = [
    (eid, meta)
    for eid, meta in zip(all_ids, all_metas)
    if meta.get("wing") == "aria"
]

print(f"\n{'═'*60}")
print("  MIGRATION wing=aria → wing=aria_episodic")
print(f"  Palace : {PALACE_PATH}")
print(f"  Mode   : {'DRY-RUN (aucune écriture)' if DRY_RUN else '*** EXÉCUTION RÉELLE ***'}")
print(f"{'═'*60}")
print(f"\n  Total entrées dans la collection : {len(all_ids)}")
print(f"  Candidats à migrer (wing=aria)   : {len(candidates)}")
print(f"  Déjà corrects (aria_episodic)    : {sum(1 for m in all_metas if m.get('wing') == 'aria_episodic')}")
print(f"  Intacts (aria_classifier)        : {sum(1 for m in all_metas if m.get('wing') == 'aria_classifier')}")

# ── Répartition des candidats par type / room ─────────────────────────────────

types = Counter(m.get("type", "?") for _, m in candidates)
rooms = Counter(m.get("room", "?") for _, m in candidates)

print(f"\n  Répartition par type :")
for k, v in types.most_common():
    print(f"    {k!r:30s} {v}")

print(f"\n  Répartition par room (top 15) :")
for k, v in rooms.most_common(15):
    print(f"    {k!r:40s} {v}")

if DRY_RUN:
    print(f"\n  {SEP}")
    print("  Dry-run terminé — aucune modification effectuée.")
    print("  Relancer avec --execute pour appliquer la migration.")
    print(f"  {SEP}\n")
    sys.exit(0)

# ── Migration par batch ───────────────────────────────────────────────────────

print(f"\n  Démarrage de la migration ({len(candidates)} entrées)...")

migrated = 0
for i in range(0, len(candidates), BATCH_SIZE):
    batch = candidates[i:i + BATCH_SIZE]
    batch_ids   = [eid for eid, _ in batch]
    batch_metas = []
    for _, meta in batch:
        new_meta = dict(meta)
        new_meta["wing"] = "aria_episodic"
        batch_metas.append(new_meta)

    col.update(ids=batch_ids, metadatas=batch_metas)
    migrated += len(batch)
    print(f"    {migrated}/{len(candidates)} entrées migrées…")

# ── Vérification post-migration ───────────────────────────────────────────────

data2 = col.get(include=["metadatas"])
wings_after = Counter(m.get("wing", "?") for m in data2["metadatas"])

print(f"\n  {SEP}")
print("  Migration terminée. État final :")
for k, v in wings_after.most_common():
    print(f"    {k!r:30s} {v}")
print(f"  {SEP}\n")
