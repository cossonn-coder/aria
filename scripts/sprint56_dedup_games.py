#!/usr/bin/env python3
# scripts/sprint56_dedup_games.py
#
# Nettoyage sprint 56 des fiches `chess_game` en double : deux fiches sont la même
# partie si les coups de l'une sont le début de ceux de l'autre et si l'adversaire
# est le même (règle `_same_game` du chess_router). La plus longue est gardée,
# la plus courte supprimée.
#
# Lecture via le bridge (règle 2), écriture via le writer (règle 1).
#
# Usage :
#   python scripts/sprint56_dedup_games.py          # liste les paires, ne touche à rien
#   python scripts/sprint56_dedup_games.py --apply  # supprime les fiches les plus courtes

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution.routers.chess_router import _same_game
from logger import get_logger
from memory.mempalace_bridge import MempalaceBridge
from memory.mempalace_store import get_by_metadata, search
from memory.writer import delete_chess_games

log = get_logger(__name__)


def _ucis(game: dict) -> list:
    return [p["uci"] for p in json.loads(game.get("plies_json") or "[]")]


def find_pairs(games: list) -> list:
    """Paires (gardée, supprimée) : la plus longue est gardée."""
    pairs = []
    for i, a in enumerate(games):
        for b in games[i + 1:]:
            if _same_game(a, _ucis(b), {(b.get("opponent") or "").lower()}):
                keep, drop = (a, b) if len(_ucis(a)) >= len(_ucis(b)) else (b, a)
                pairs.append((keep, drop))
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="supprime les fiches les plus courtes")
    args = parser.parse_args()

    # Même construction que bot.py ; load_chess_games lit config.mempalace_path.
    games = MempalaceBridge(store=search, get_by_metadata=get_by_metadata).load_chess_games()
    pairs = find_pairs(games)
    print(f"\n  Fiches lues : {len(games)}")
    print(f"  Paires « même partie » : {len(pairs)}")
    for keep, drop in pairs:
        print(f"    garde {keep['id']} ({len(_ucis(keep))})  supprime {drop['id']} "
              f"({len(_ucis(drop))})  contre {drop.get('opponent')}")
    if not args.apply or not pairs:
        return
    doomed = sorted({drop["id"] for _, drop in pairs})
    delete_chess_games(doomed)
    log.info("sprint56_dedup deleted=%s", doomed)
    print(f"\n  Supprimées : {len(doomed)}")


if __name__ == "__main__":
    main()
