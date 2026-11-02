# tests/chess_coach/test_structure.py
#
# Faits structurels d'une position (sprint 46, tronçon 02).

from chess_coach.structure import structure_line

# Blancs : Ra1 Nb1 Bc1 Qd1 Rf1 Kg1, pions b2 d4 f2 g2 h2.
# Noirs : Ra8 Nb8 Qd8 Ke8 Bf8 Ng8 Rh8, pions a7 f7 g7 h7 h6.
_FEN = "rn1qkbnr/p4ppp/7p/8/3P4/8/1P3PPP/RNBQ1RK1 w kq - 0 10"


def test_structure_line_from_white_side():
    assert structure_line(_FEN, "white") == (
        "colonnes ouvertes : c, e ; "
        "colonnes semi-ouvertes pour Nico : a ; "
        "colonnes semi-ouvertes pour l'adversaire : b, d ; "
        "pions isolés : Nico b2 d4, adversaire a7 ; "
        "pions doublés : adversaire h6 h7 ; "
        "pions passés : Nico d4 ; "
        "roi de Nico : g1, roqué, 3 pions devant ; "
        "roi adverse : e8, au centre, 1 pion devant ; "
        "pièces mineures sur leur case de départ : Nico Nb1 Bc1, adversaire Nb8 Bf8 Ng8"
    )


def test_structure_line_swaps_sides_for_black():
    line = structure_line(_FEN, "black")
    assert "colonnes semi-ouvertes pour Nico : b, d" in line
    assert "pions passés : adversaire d4" in line
    assert "roi de Nico : e8, au centre, 1 pion devant" in line
    assert "roi adverse : g1, roqué, 3 pions devant" in line


def test_structure_line_hides_empty_categories():
    # Position de départ : aucune colonne ouverte, aucun pion remarquable.
    line = structure_line("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "white")
    assert "colonnes" not in line
    assert "pions isolés" not in line
    assert line.startswith("roi de Nico : e1, au centre, 3 pions devant")
