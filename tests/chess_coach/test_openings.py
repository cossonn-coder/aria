# tests/chess_coach/test_openings.py
#
# Détection d'ouverture (sprint 46, tronçon 03) : table Lichess réelle, pas de palace.

import pytest

from chess_coach.openings import detect_opening, opening_group, opening_room


def test_detect_goring():
    eco, name = detect_opening(["e2e4", "e7e5", "g1f3", "b8c6", "d2d4", "e5d4", "c2c3"])
    assert eco == "C44" and name == "Scotch Game: Göring Gambit"


def test_detect_von_hennig_caro_kann():
    _, name = detect_opening(["e2e4", "c7c6", "d2d4", "d7d5", "b1c3", "d5e4", "f1c4"])
    assert name == "Caro-Kann Defense: von Hennig Gambit"


def test_detect_keeps_last_known_position_and_transposition():
    # 1.d4 e6 2.e4 rejoint le French par transposition ; le coup suivant, hors table, ne l'efface pas.
    _, name = detect_opening(["d2d4", "e7e6", "e2e4"])
    assert name.startswith("French Defense")
    assert detect_opening(["d2d4", "e7e6", "e2e4", "h7h5"])[1] == name


@pytest.mark.parametrize("name, label", [
    ("Scotch Game: Göring Gambit, Main Line", "Göring Gambit"),
    ("Scotch Game: Scotch Gambit, Göring Gambit Declined", "Göring Gambit"),
    ("Scotch Game: Scotch Gambit, Advance Variation", "Scotch Gambit"),
    ("Italian Game: Rousseau Gambit", "Rousseau Gambit"),
    ("Dutch Defense: Alapin Variation", "Dutch Defense"),
    ("Benko Gambit Accepted", "Benko Gambit"),
    ("Scandinavian Defense: Icelandic-Palme Gambit", "Icelandic Gambit"),
    ("Sicilian Defense: Portsmouth Gambit", "Portsmouth Gambit"),
    ("Sicilian Defense: Wing Gambit, Deferred Variation", "Delayed Wing Gambit"),
    ("French Defense: Alapin Gambit", "Alapin Gambit"),
    ("Blackmar-Diemer Gambit: von Popiel Gambit", "von Popiel Gambit"),
    ("Caro-Kann Defense: von Hennig Gambit", "von Hennig Gambit"),
    ("Tarrasch Defense: von Hennig Gambit", "von Hennig Gambit"),
    ("Englund Gambit: Hartlaub-Charlick Gambit", "Hartlaub-Charlick Gambit"),
    ("King's Pawn Game: Busch-Gass Gambit, Chiodini Gambit", "Busch-Gass Gambit"),
    ("Ruy Lopez: Steinitz Defense", "Ruy Lopez"),
])
def test_opening_group(name, label):
    assert opening_group(name) == label


def test_opening_room():
    assert opening_room("Göring Gambit") == "chess_goring-gambit"
    assert opening_room(None) == "chess"
