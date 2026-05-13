# scripts/embedder_bench/cleanup_intent_fantome.py
#
# Désactive les intents fantômes identifiés dans T-Embedder1 — ces intents
# ont été créés par le bug SPLIT (dette #23, naming brut message[:60])
# et polluent le matching en devenant top-1 sur tout message contenant
# le préfixe tronqué.
#
# Méthode : passe `status` à "completed" + ajoute une action de traçabilité
# `deactivated_T-Embedder2:<iso>`. **Pas de suppression dure** — les
# entrées restent dans `intents.json` pour audit/historique. La logique
# IntentStore filtre les intents `completed` lors du recall (cf.
# audit sprint 5 §4 description du store).
#
# Liste des préfixes d'ID est en dur dans le code (pas en argument CLI) :
# le diff git trace le « quoi » et le « pourquoi », l'invocation reste
# triviale (`./venv/bin/python scripts/embedder_bench/cleanup_intent_fantome.py`).
#
# Script idempotent : si un intent ciblé est déjà `completed`, skip silencieux.
# Snapshot ~/.aria/intents.json.bak.<timestamp> avant toute modif.
#
# Dépendances : aucune (stdlib uniquement).

from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

INTENTS_PATH = Path(os.path.expanduser("~/.aria/intents.json"))

# Liste des préfixes d'ID des intents fantômes à désactiver.
# Audit T-Embedder1 §2.3 (audit_embedder_benchmark.md) cas C5_T4 :
# bug SPLIT brut a créé un intent dont le name est message[:60] tronqué,
# qui devient top-1 sur tout message contenant « cuisine » ou « cocotte ».
GHOST_PREFIXES: list[str] = [
    "ed1bf159",  # "Dans ma cuisine j'ai : Une cocotte, une poêle, une planche à"
]


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def main() -> int:
    if not INTENTS_PATH.exists():
        print(f"[ERREUR] {INTENTS_PATH} introuvable.", file=sys.stderr)
        return 2

    data = json.loads(INTENTS_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        print(f"[ERREUR] {INTENTS_PATH} : schéma inattendu (attendu dict).", file=sys.stderr)
        return 2

    # Repérage
    targets = []
    for key, item in data.items():
        if not isinstance(item, dict):
            continue
        if not any(key.startswith(p) for p in GHOST_PREFIXES):
            continue
        targets.append((key, item))

    if not targets:
        print("Aucun intent fantôme matché par les préfixes en dur — rien à faire.")
        return 0

    # Snapshot avant modif
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = INTENTS_PATH.with_name(f"intents.json.bak.{ts}")
    shutil.copy2(INTENTS_PATH, backup)
    print(f"Snapshot : {backup}")

    # Application
    iso = _now_iso()
    n_changed = 0
    n_skipped = 0
    for key, item in targets:
        name = (item.get("name") or "")[:60]
        status = item.get("status")
        if status == "completed":
            print(f"  skip (déjà completed) : id={key} name={name!r}")
            n_skipped += 1
            continue

        item["status"] = "completed"
        history = item.setdefault("actions_history", [])
        history.append(f"deactivated_T-Embedder2:{iso}")
        print(f"  done : id={key} name={name!r} action='deactivated_T-Embedder2:{iso}'")
        n_changed += 1

    if n_changed == 0:
        print("Aucune modification (tous les intents ciblés étaient déjà completed).")
        # Snapshot inutile — on pourrait le supprimer, mais on garde pour audit.
        return 0

    # Écriture atomique : write tmp + replace
    tmp = INTENTS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, INTENTS_PATH)
    print(f"\n{n_changed} intent(s) désactivé(s), {n_skipped} skip(s).")
    print(f"Fichier mis à jour : {INTENTS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
