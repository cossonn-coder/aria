# docs/sprint68/mesure_explosive.py
#
# Sprint 68, tronçon 03 : durée de find_explosive et coups trouvés, par réglage,
# sur un corpus de parties réelles. Lecture seule du palace par le bridge
# (comme scripts/feedback_report.py) : aucune écriture.
#
# Corpus : les 8 fiches les plus récentes dont un demi-coup de plies_json porte
# kind == "d" (miniature explosive). minis_json n'existe que sur 2 fiches
# (sprint 66), d'où plies_json.
#
# Usage : ./venv/bin/python docs/sprint68/mesure_explosive.py ref torch1 deep2 …
# Chaque réglage nommé est mesuré dans l'ordre ; le premier sert de référence
# pour les écarts. Le bloc de résultats est ajouté à mesure_explosive.txt.
# Depuis le tronçon 03, find_explosive force lui-même 1 thread torch : « ref » et
# « torch1 » mesurent désormais la même chose (les blocs consignés datent d'avant).
# Sortie par sys.stdout : script de mesure hors service.

import json
import os
import pickle
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import chess.pgn  # noqa: E402
import torch  # noqa: E402

from chess_coach import explosive  # noqa: E402
from chess_coach.analysis import analyze_game  # noqa: E402
from config import config  # noqa: E402

OUT = Path(__file__).with_suffix(".txt")
# Plies de analyze_game mis en cache (déterministe : nœuds fixes, hash vidé) ;
# /tmp est plein sur la VM.
CACHE = Path.home() / ".cache" / "aria_s68_explosive_plies.pkl"
CORPUS = 8

# Réglages : (threads torch ou None, _MAX_DEEP, _DEEP_TIME).
SETTINGS = {
    "ref": (None, 3, 0.3),
    "torch1": (1, 3, 0.3),
    "torch2": (2, 3, 0.3),
    "torch1_deep2": (1, 2, 0.3),
    "torch1_deep2_time02": (1, 2, 0.2),
    "deep2": (None, 2, 0.3),
    "time02": (None, 3, 0.2),
}

lines = []


def out(text=""):
    lines.append(text)
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


def load_corpus() -> list:
    """Les CORPUS fiches les plus récentes avec une miniature explosive dans plies_json."""
    from memory.mempalace_bridge import MempalaceBridge
    from memory.mempalace_store import get_by_metadata, search

    bridge = MempalaceBridge(store=search, get_by_metadata=get_by_metadata)
    games = [g for g in bridge.load_chess_games() if g.get("plies_json")
             and any(p.get("kind") == "d" for p in json.loads(g["plies_json"]))]
    return games[-CORPUS:]


def replay(fiche: dict) -> chess.pgn.Game:
    """Partie rejouée depuis les coups uci de plies_json."""
    game = chess.pgn.Game()
    node = game
    for p in json.loads(fiche["plies_json"]):
        node = node.add_variation(chess.Move.from_uci(p["uci"]))
    return game


def corpus_plies() -> list:
    """[(id, nico_color, elo_opponent, plies)] ; analyze_game fait une seule fois (cache)."""
    if CACHE.exists():
        return pickle.loads(CACHE.read_bytes())
    data = []
    for fiche in load_corpus():
        started = time.monotonic()
        plies = analyze_game(replay(fiche), fiche["nico_color"], config.stockfish_path)
        out(f"analyze_game {fiche['id']} {len(plies)} demi-coups {time.monotonic() - started:.1f} s")
        elo = fiche.get("elo_opponent")
        data.append((fiche["id"], fiche["nico_color"], int(elo) if elo else None, plies))
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(pickle.dumps(data))
    return data


def cpu_seconds() -> float:
    """Temps CPU du processus (Maia) + des Stockfish fermés (enfants), en secondes.

    Moins sensible que la durée murale à la charge des autres processus.
    """
    own, children = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
    return own.ru_utime + own.ru_stime + children.ru_utime + children.ru_stime


def run(name: str, corpus: list) -> tuple:
    """Durée totale, temps CPU et résultats {id: {(ply, uci): replies}} d'un réglage."""
    threads, max_deep, deep_time = SETTINGS[name]
    default_threads = torch.get_num_threads()
    if threads:
        torch.set_num_threads(threads)
    explosive._MAX_DEEP, explosive._DEEP_TIME = max_deep, deep_time
    total, found = 0.0, {}
    cpu_start = cpu_seconds()
    try:
        for game_id, color, elo, plies in corpus:
            started = time.monotonic()
            result = explosive.find_explosive(plies, color, config.stockfish_path, elo,
                                              config.maia_models_dir, first_move=1)
            duration = time.monotonic() - started
            total += duration
            found[game_id] = {
                (c.ply.ply, c.explosive.uci): [(r["san"], round(r["p"], 4)) for r in c.explosive.replies]
                for c in result
            }
            out(f"  {name} {game_id} {duration:.1f} s found={sorted(found[game_id])}")
    finally:
        torch.set_num_threads(default_threads)
        explosive._MAX_DEEP, explosive._DEEP_TIME = 3, 0.3
    return total, cpu_seconds() - cpu_start, found


def main():
    names = sys.argv[1:] or ["ref"]
    out(f"=== {time.strftime('%Y-%m-%d %H:%M')} réglages={names} charge={os.getloadavg()[0]:.1f} "
        f"torch par défaut={torch.get_num_threads()} threads")
    corpus = corpus_plies()
    # Liste et non dict : un réglage peut être répété (bruit de charge).
    results = [(name, *run(name, corpus)) for name in names]
    _, ref_total, _, ref_found = results[0]
    out()
    out(f"| Réglage | Durée totale [{len(corpus)} parties] | CPU (Maia + Stockfish) | Coups trouvés | Écart (ply, uci) vs {names[0]} | Réponses Maia identiques |")
    out("|---|---|---|---|---|---|")
    for name, total, cpu, found in results:
        moves = sum(len(f) for f in found.values())
        diff = [(g, sorted(set(found[g]) ^ set(ref_found[g]))) for g in found if set(found[g]) != set(ref_found[g])]
        same_replies = all(found[g].get(k) == v for g in ref_found for k, v in ref_found[g].items() if k in found[g])
        out(f"| {name} | {total:.1f} s | {cpu:.0f} s | {moves} | {diff or 'aucun'} | {'oui' if same_replies else 'non'} |")
    out(f"charge en fin={os.getloadavg()[0]:.1f}")
    out()
    with OUT.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
