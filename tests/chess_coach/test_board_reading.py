# tests/chess_coach/test_board_reading.py
#
# Sprint 59, tronçon 01 : grille lue sur une image → FEN.

from pathlib import Path

from chess_coach.board_reading import grid_to_fen, position_problem

_GRID = (Path(__file__).parents[2] / "docs/sprint59/ref/chesscom_vert.txt").read_text().split()
_FEN = "r1bqkb1r/pp3ppp/2n2n2/2pp4/2B5/2NP1N2/PPP2PPP/R1BQK2R b KQkq - 0 1"


def test_grid_with_caption_black_to_move():
    assert grid_to_fen(_GRID, "trait aux noirs") == (_FEN, "black")


def test_grid_without_caption_bottom_side_to_move():
    # Noirs en bas : le trait leur revient.
    assert grid_to_fen(_GRID, None) == (_FEN, "black")


def test_two_white_kings_is_a_problem():
    assert position_problem("4k3/8/8/8/8/8/8/K3K3 w - - 0 1") is not None
