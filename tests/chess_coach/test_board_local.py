# tests/chess_coach/test_board_local.py
#
# Sprint 59, tronçon 02 : lecteur local de secours (captures d'écran).

from pathlib import Path

import numpy as np
from PIL import Image

from chess_coach.board_local import read_board

_ROOT = Path(__file__).parents[2]
_REF = _ROOT / "chess_coach/data/board_refs/chesscom_vert.jpg"
_GRID = (_ROOT / "chess_coach/data/board_refs/chesscom_vert.txt").read_text().split()


def test_reads_reference_capture():
    assert read_board(_REF) == _GRID


def test_reads_board_inside_full_screen_capture(tmp_path):
    # Capture plein écran simulée : fond uni, bandeaux d'une autre couleur, plateau agrandi décalé.
    screen = Image.new("RGB", (1080, 1920), (40, 40, 48))
    screen.paste((200, 60, 60), (0, 0, 1080, 180))
    screen.paste((200, 60, 60), (0, 1740, 1080, 1920))
    board = Image.open(_REF).convert("RGB").resize((400, 397))
    screen.paste(board, (137, 611))
    path = tmp_path / "screen.png"
    screen.save(path)
    assert read_board(path) == _GRID


def test_no_board_returns_none(tmp_path):
    ramp = np.tile(np.linspace(0, 255, 600, dtype=np.uint8)[:, None, None], (1, 400, 3))
    path = tmp_path / "ramp.png"
    Image.fromarray(ramp).save(path)
    assert read_board(path) is None
