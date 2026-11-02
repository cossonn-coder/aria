#!/usr/bin/env python3
# scripts/migrate_chess_rooms.py
#
# Migration sprint 46 des fiches `chess_game` :
#   - supprime les fiches dont l'adversaire est un pseudo de Nico (analysées du
#     mauvais camp, décision Q9) ;
#   - range les autres dans la room de leur ouverture, sans toucher au timestamp,
#     aux coups ni au document. Une fiche non reconnue est signalée et laissée telle quelle.
#
# Lecture via le bridge (règle 2), écriture via le writer (règle 1).
#
# Usage :
#   python scripts/migrate_chess_rooms.py [--palace CHEMIN]          # essai à blanc
#   python scripts/migrate_chess_rooms.py [--palace CHEMIN] --apply  # migration réelle

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chess_coach.openings import detect_opening, opening_group, opening_room
from config import config
from logger import get_logger
from memory.mempalace_bridge import MempalaceBridge
from memory.mempalace_store import get_by_metadata, search
from memory.writer import delete_chess_games, update_chess_game_opening

log = get_logger(__name__)

# Suppressions attendues sur la prod au 2026-11-02 (Q9), comparées au plan calculé.
EXPECTED_DELETIONS = {
    "chess_game_13b7dfa511210031", "chess_game_77fe80051db8b240", "chess_game_dce2b1804d94b7eb",
    "chess_game_6f1e3bb987feeecb", "chess_game_204a4207b294a118", "chess_game_2f3a3b1f3a18e216",
    "chess_game_991140ab8fbb3116", "chess_game_f8eeb32ca876ec9f", "chess_game_8ef649fb688185e3",
}


@dataclass
class Plan:
    deletions: list = field(default_factory=list)     # fiches à supprimer
    updates: list = field(default_factory=list)       # {doc_id, room, opening, opening_group, eco}
    unrecognized: list = field(default_factory=list)  # fiches sans ouverture détectée
    rooms: Counter = field(default_factory=Counter)   # room → fiches conservées, après migration


def build_plan(games: list) -> Plan:
    """Plan de migration, sans écriture. Une fiche déjà rangée ne produit aucune mise à
    jour : c'est ce qui rend le script idempotent."""
    own_names = {name.lower() for name in (*config.chess_usernames, "Nico")}
    plan = Plan()
    for game in games:
        if (game.get("opponent") or "").lower() in own_names:
            plan.deletions.append(game)
            continue
        ucis = [ply["uci"] for ply in json.loads(game.get("plies_json") or "[]")]
        detected = detect_opening(ucis)
        if detected is None:
            plan.unrecognized.append(game)
            plan.rooms[game.get("room")] += 1
            continue
        eco, name = detected
        group = opening_group(name)
        target = {
            "room": opening_room(group),
            "opening": name,
            "opening_group": group,
            "eco": game.get("eco") or eco,
        }
        plan.rooms[target["room"]] += 1
        if any(game.get(key) != value for key, value in target.items()):
            plan.updates.append({"doc_id": game["id"], **target})
    return plan


def load_games() -> list:
    # Même construction que bot.py ; load_chess_games lit config.mempalace_path.
    return MempalaceBridge(store=search, get_by_metadata=get_by_metadata).load_chess_games()


def service_blocks(palace: str, config_palace: str) -> bool:
    """Vrai si le service tourne sur le palace visé : il faut l'arrêter avant d'écrire."""
    if os.path.realpath(palace) != os.path.realpath(config_palace):
        return False
    state = subprocess.run(["systemctl", "is-active", "aria"], capture_output=True, text=True)
    return state.stdout.strip() == "active"


def print_plan(plan: Plan, total: int) -> None:
    print(f"\n  Fiches lues : {total}")
    print(f"\n  À supprimer : {len(plan.deletions)}")
    for game in plan.deletions:
        print(f"    {game['id']}  contre {game.get('opponent')}")
    if plan.deletions:
        ids = {game["id"] for game in plan.deletions}
        print(f"    Hors liste attendue : {sorted(ids - EXPECTED_DELETIONS) or 'aucune'}")
        print(f"    Attendues absentes  : {sorted(EXPECTED_DELETIONS - ids) or 'aucune'}")
    print(f"\n  À mettre à jour : {len(plan.updates)}")
    print("\n  Fiches par room après migration :")
    for room, count in plan.rooms.most_common():
        print(f"    {room:40s} {count}")
    print(f"\n  Non reconnues : {len(plan.unrecognized)}")
    for game in plan.unrecognized:
        print(f"    {game['id']}  contre {game.get('opponent')}")


def check_migration(before: list, n_deleted: int) -> list:
    """Relit le palace et renvoie la liste des écarts (vide si tout est conforme)."""
    after = load_games()
    gaps = []
    if len(after) != len(before) - n_deleted:
        gaps.append(f"{len(after)} fiches au lieu de {len(before) - n_deleted}")
    original = {game["id"]: game for game in before}
    for game in after:
        for key in ("timestamp", "plies_json"):
            if game.get(key) != original[game["id"]].get(key):
                gaps.append(f"{game['id']} : {key} modifié")
    # Le plan recalculé doit être vide : plus de pseudo adverse, tout est rangé.
    plan = build_plan(after)
    gaps += [f"{game['id']} : pseudo adverse restant" for game in plan.deletions]
    gaps += [f"{update['doc_id']} : mise à jour non appliquée" for update in plan.updates]
    return gaps


def main(argv: list | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migration sprint 46 des fiches de parties.")
    parser.add_argument("--palace", default=config.mempalace_path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)

    palace = os.path.abspath(args.palace)
    config_palace = config.mempalace_path
    # Writer et bridge lisent ce champ à chaque appel.
    config.mempalace_path = palace

    print(f"\n  Palace : {palace}")
    print(f"  Mode   : {'*** EXÉCUTION RÉELLE ***' if args.apply else 'essai à blanc (aucune écriture)'}")

    games = load_games()
    plan = build_plan(games)
    print_plan(plan, len(games))

    if not args.apply:
        print("\n  Essai à blanc terminé. Relancer avec --apply pour migrer.\n")
        return 0

    if service_blocks(palace, config_palace):
        print("\n  REFUS : aria.service est actif sur ce palace. L'arrêter d'abord.\n")
        return 1

    if not plan.deletions and not plan.updates:
        print("\n  Rien à faire : palace déjà migré, aucune écriture.\n")
        return 0

    backup = f"{palace}.pre-sprint46-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copytree(palace, backup)
    print(f"\n  Sauvegarde : {backup}")
    log.info("migrate_chess_rooms backup=%s", backup)

    if plan.deletions:
        delete_chess_games([game["id"] for game in plan.deletions])
    for update in plan.updates:
        update_chess_game_opening(**update)
    log.info("migrate_chess_rooms deleted=%d updated=%d", len(plan.deletions), len(plan.updates))

    gaps = check_migration(games, len(plan.deletions))
    if gaps:
        print(f"\n  ÉCARTS ({len(gaps)}) :")
        for gap in gaps:
            print(f"    {gap}")
        log.error("migrate_chess_rooms gaps=%d", len(gaps))
        return 1

    print(f"\n  Migration conforme : {len(plan.deletions)} supprimées, {len(plan.updates)} mises à jour, "
          f"{len(games) - len(plan.deletions)} fiches restantes.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
