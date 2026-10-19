# tests/chess_coach/test_chess_coach.py
#
# Cas nominaux du paquet chess_coach (sprint 26, tronçon 01).

from pathlib import Path

import pytest
from PIL import Image

from chess_coach.analysis import analyze, detect_color
from chess_coach.notation import to_french
from chess_coach.render import SIZE, render_position

STOCKFISH = "/usr/games/stockfish"

SCHOLAR_PGN = """je joue les noirs
[White "Ami"]
[Black "staroflexeur"]
1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0
"""


def test_to_french():
    assert to_french("Nxe5") == "Cxe5"
    assert to_french("e8=Q+") == "e8=D+"
    assert to_french("Kf2") == "Rf2"


def test_detect_color():
    assert detect_color({"White": "Ami", "Black": "StarOflexeur"}, "", "staroflexeur") == ("black", "header")
    assert detect_color({"White": "Ami", "Black": "Moi"}, "je joue les noirs", "staroflexeur") == ("black", "message")
    assert detect_color({"White": "Ami", "Black": "Moi"}, "", "staroflexeur") == ("white", "default")


@pytest.mark.skipif(not Path(STOCKFISH).exists(), reason="Stockfish absent")
def test_analyze_detects_blunder():
    game = analyze(SCHOLAR_PGN, SCHOLAR_PGN, "staroflexeur", STOCKFISH)
    assert game.nico_color == "black"
    blunder = game.plies[5]
    assert blunder.san == "Nf6"
    assert blunder.quality == "blunder"
    assert any(c.kind == "a" and c.ply.ply == 5 for c in game.critical)


def test_render_position(tmp_path):
    out = tmp_path / "pos.png"
    fen = "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3"
    assert render_position(fen, "black", "g8f6", str(out)) == str(out)
    with Image.open(out) as image:
        assert image.size == (SIZE, SIZE)
