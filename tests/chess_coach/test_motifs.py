# tests/chess_coach/test_motifs.py
#
# Tests de chess_coach.motifs (sprint 29, tronçon 02) : une position construite
# à la main par motif principal. Format : position AVANT le coup adverse, coup
# adverse, puis meilleur coup de Nico et suite de la ligne.

from chess_coach.motifs import tag_motifs


def test_knight_fork():
    # Cc7+ fourchette le roi e8 et la tour a8, puis Cxa8.
    tags = tag_motifs("r3k3/7p/8/3N4/8/8/8/6K1 b - - 0 1", "h7h6", ["d5c7", "e8d7", "c7a8"])
    assert "fork" in tags


def test_pin():
    # Fb5 cloue la tour d7 sur le roi e8.
    tags = tag_motifs("4k3/p2r3p/8/8/8/8/8/5BK1 b - - 0 1", "h7h6", ["f1b5"])
    assert "pin" in tags


def test_skewer():
    # Te7+ en enfilade : le roi quitte la colonne, la dame e2 tombe.
    tags = tag_motifs("8/R6p/8/4k3/8/8/4q3/7K b - - 0 1", "h7h6", ["a7e7", "e5f5", "e7e2"])
    assert "skewer" in tags


def test_discovered_attack():
    # Cc5 démasque la tour e1 : échec à la découverte.
    tags = tag_motifs("4k3/p7/8/8/4N3/8/8/4R1K1 b - - 0 1", "a7a6", ["e4c5"])
    assert "discoveredAttack" in tags


def test_smothered_mate():
    tags = tag_motifs("6rk/p5pp/8/6N1/8/8/8/6K1 b - - 0 1", "a7a6", ["g5f7"])
    assert "smotheredMate" in tags


def test_back_rank_mate():
    tags = tag_motifs("6k1/1p3ppp/8/8/8/8/8/R5K1 b - - 0 1", "b7b6", ["a1a8"])
    assert "backRankMate" in tags


def test_triangle_mate():
    # Dd7# avec la tour f7 : dame et tour adjacentes au roi e8, sur la 7e rangée.
    tags = tag_motifs("4k3/p4R2/8/8/8/8/8/3Q2K1 b - - 0 1", "a7a6", ["d1d7"])
    assert "triangleMate" in tags
