#!/usr/bin/env python3
# scripts/backfill_chess_accuracy.py
#
# Rattrapage sprint 55 des fiches `chess_game` :
#   - supprime les fiches parasites (adversaire « Test » ou « Ami ») ;
#   - pose la précision de Nico sur les fiches qui n'en ont pas, recalculée depuis
#     plies_json avec la formule du bilan (_game_accuracy), sans relancer le moteur.
#
# Lecture via le bridge (règle 2), écriture via le writer (règle 1).
#
# Usage :
#   python scripts/backfill_chess_accuracy.py            # essai à blanc
#   python scripts/backfill_chess_accuracy.py --apply    # exécution réelle (service arrêté)

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_coach.summary import _game_accuracy
from config import config
from logger import get_logger
from memory.writer import delete_chess_games, update_chess_game_accuracy
from scripts.migrate_chess_rooms import load_games, service_blocks

log = get_logger(__name__)


def build_plan(games: list) -> tuple[list, list]:
    """(fiches de test à supprimer, [(doc_id, précision)] à poser). Une fiche qui a déjà
    sa précision ne produit rien : le script est idempotent."""
    deletions = [g for g in games if (g.get("opponent") or "") in ("Test", "Ami")]
    updates = []
    for g in games:
        if g in deletions or g.get("accuracy") is not None:
            continue
        plies = [SimpleNamespace(**p) for p in json.loads(g["plies_json"])]
        updates.append((g["id"], _game_accuracy(plies, g["nico_color"])))
    return deletions, updates


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rattrapage sprint 55 de la précision des fiches.")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    games = load_games()
    deletions, updates = build_plan(games)
    print(f"\n  Fiches lues : {len(games)}")
    print(f"  À supprimer (Test, Ami) : {[g['id'] for g in deletions]}")
    print(f"  Précision à poser : {len(updates)}")
    for doc_id, accuracy in updates:
        print(f"    {doc_id}  {accuracy} %")

    if not args.apply:
        print("\n  Essai à blanc terminé. Relancer avec --apply pour écrire.\n")
        return 0
    if service_blocks(config.mempalace_path, config.mempalace_path):
        print("\n  REFUS : aria.service est actif. L'arrêter d'abord.\n")
        return 1
    if not deletions and not updates:
        print("\n  Rien à faire.\n")
        return 0

    backup = f"{config.mempalace_path}.pre-sprint55-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copytree(config.mempalace_path, backup)
    print(f"\n  Sauvegarde : {backup}")
    log.info("backfill_chess_accuracy backup=%s", backup)

    if deletions:
        delete_chess_games([g["id"] for g in deletions])
    for doc_id, accuracy in updates:
        update_chess_game_accuracy(doc_id, accuracy)
    log.info("backfill_chess_accuracy deleted=%d updated=%d", len(deletions), len(updates))

    # Contrôle : relire, plus rien à faire, et le bon nombre de fiches.
    after = load_games()
    left = build_plan(after)
    if len(after) != len(games) - len(deletions) or left != ([], []):
        print(f"\n  ÉCART : {len(after)} fiches, reste {left}\n")
        log.error("backfill_chess_accuracy gaps")
        return 1
    print(f"\n  Conforme : {len(deletions)} supprimées, {len(updates)} précisions posées, {len(after)} fiches.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
