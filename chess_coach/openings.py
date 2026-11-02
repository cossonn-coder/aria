# aria/chess_coach/openings.py
#
# Détection de l'ouverture à partir des coups joués (sprint 46, tronçon 03).
#
# Ni Stockfish ni Maia ne nomment une ouverture : d'où une table de positions.
# Source de data/openings.tsv : https://github.com/lichess-org/chess-openings
# (licence CC0), concaténation de a.tsv à e.tsv, 3 865 positions.
# La clé est la position et non la suite de coups : les transpositions sont
# donc reconnues. Module pur : aucun import mémoire / LLM / exécution.

import csv
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import chess

_TABLE_PATH = Path(__file__).parent / "data" / "openings.tsv"

# Une ligne par ouverture : libellé → préfixes de nom Lichess. Testés dans cet
# ordre, le 1er gagne : Göring passe donc avant Scotch Gambit, dont un nom
# (« Scotch Gambit, Göring Gambit Declined ») relève de lui.
OPENING_CATALOG = {
    "Göring Gambit": ("Scotch Game: Göring Gambit", "Scotch Game: Scotch Gambit, Göring Gambit Declined"),
    "Scotch Gambit": ("Scotch Game: Scotch Gambit",),
    "Rousseau Gambit": ("Italian Game: Rousseau Gambit",),
    "Dutch Defense": ("Dutch Defense",),
    "Benko Gambit": ("Benko Gambit",),
    "Icelandic Gambit": ("Scandinavian Defense: Icelandic-Palme Gambit",),
    "Portsmouth Gambit": ("Sicilian Defense: Portsmouth Gambit",),
    "Delayed Wing Gambit": ("Sicilian Defense: Wing Gambit, Deferred Variation",),
    "Alapin Gambit": ("French Defense: Alapin Gambit",),
    "von Popiel Gambit": ("Blackmar-Diemer Gambit: von Popiel Gambit",),
    "von Hennig Gambit": ("Caro-Kann Defense: von Hennig Gambit", "Tarrasch Defense: von Hennig Gambit"),
    "Hartlaub-Charlick Gambit": ("Englund Gambit: Hartlaub-Charlick Gambit",),
}


@lru_cache(maxsize=1)
def _table() -> dict:
    """Position (EPD) → (eco, name). Environ 2 s au premier appel, en cache ensuite."""
    table = {}
    with open(_TABLE_PATH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            board = chess.Board()
            for token in row["pgn"].split():
                # Les numéros de coup (« 1. ») ne sont pas des coups.
                if not token[0].isdigit():
                    board.push_san(token)
            table[board.epd()] = (row["eco"], row["name"])
    return table


def detect_opening(ucis: list[str]) -> tuple[str, str] | None:
    """(eco, name) de la dernière position connue de la table, None si aucune.
    Les coups partent de la position initiale standard."""
    table = _table()
    board = chess.Board()
    found = None
    for uci in ucis:
        board.push(chess.Move.from_uci(uci))
        found = table.get(board.epd(), found)
    return found


def opening_group(name: str) -> str:
    """Libellé du catalogue, sinon la famille : ce qui précède le premier « : » ou « , »."""
    for label, prefixes in OPENING_CATALOG.items():
        if name.startswith(prefixes):
            return label
    return re.split(r"[:,]", name, maxsplit=1)[0]


def opening_room(group: str | None) -> str:
    """Room de la fiche : chess_<slug> (minuscules, sans accents, tirets), chess si None.
    Le préfixe évite toute collision avec les rooms documents et general."""
    if group is None:
        return "chess"
    ascii_name = unicodedata.normalize("NFKD", group).encode("ascii", "ignore").decode()
    return "chess_" + re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
