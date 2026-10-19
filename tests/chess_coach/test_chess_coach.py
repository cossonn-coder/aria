# tests/chess_coach/test_chess_coach.py
#
# Cas nominaux du paquet chess_coach (sprint 26, tronçon 01).

from pathlib import Path

import chess
import pytest
from PIL import Image

from chess_coach.analysis import CriticalPosition, PlyAnalysis, analyze, detect_color, parse_pgn, select_critical
from chess_coach.explosive import _line_sacrifice
from chess_coach.render import SIZE, render_position

STOCKFISH = "/usr/games/stockfish"

SCHOLAR_PGN = """je joue les noirs
[White "Ami"]
[Black "staroflexeur"]
1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0
"""


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


MORRA_PGN = """[White "staroflexeur"]
[Black "Test"]
1. e4 c5 2. d4 cxd4 3. c3 dxc3 4. Nxc3 Nc6 5. Nf3 Nf6 6. Bc4 e6 7. O-O a6 8. e5 *
"""

QH5_PGN = """[White "Test"]
[Black "staroflexeur"]
1. e4 e5 2. Qh5 Nc6 *
"""


@pytest.mark.skipif(not Path(STOCKFISH).exists(), reason="Stockfish absent")
def test_explosive_smith_morra_nd5():
    # Sprint 27 : 8.Cd5!? tend un piège (8…exd5 fait perdre ≥ 10 pts aux noirs).
    game = analyze(MORRA_PGN, MORRA_PGN, "staroflexeur", STOCKFISH)
    d = next(c for c in game.critical if c.kind == "d" and c.ply.move_number == 8)
    assert d.explosive.san == "Nd5"
    assert d.explosive.trap >= 10
    # Tronçon 05 : le cavalier offert (attaqué par e6) compte même refusé dans la PV.
    assert d.explosive.offered == 3
    assert d.explosive.sacrifice >= 3
    assert d.explosive.trap_line_san[0] == "exd5"
    assert d.explosive.replies


@pytest.mark.skipif(not Path(STOCKFISH).exists(), reason="Stockfish absent")
def test_explosive_early_queen_nf6():
    # Sprint 27 : 2…Cf6 sacrifie e5 (3.Dxe5+ Fe7).
    game = analyze(QH5_PGN, QH5_PGN, "staroflexeur", STOCKFISH)
    d = next(c for c in game.critical if c.kind == "d" and c.ply.move_number == 2)
    assert d.explosive.san == "Nf6"
    assert d.explosive.sacrifice >= 1


def test_line_sacrifice_waits_end_of_exchange():
    # Tronçon 05 : 1...d6 2.d4 e5 3.dxe5 dxe5 4.Dxd8+ Rxd8 — la dame est reprise, sacrifice 0.
    board = chess.Board()
    board.push_san("e4")
    line = []
    replay = board.copy()
    for san in ["d6", "d4", "e5", "dxe5", "dxe5", "Qxd8+", "Kxd8"]:
        line.append(replay.push_san(san))
    assert _line_sacrifice(board, line) == (0, 7)


def _ply(ply, loss, second_gap=None, move_number=None):
    return PlyAnalysis(
        ply=ply, move_number=move_number or ply // 2 + 1, color="white" if ply % 2 == 0 else "black", san="e4", uci="e2e4",
        fen_before=chess.STARTING_FEN, win_before=50.0, win_after=50.0 - loss, loss=loss,
        best_san="e4", best_uci="e2e4", pv_san=["e4"], second_gap=second_gap,
        quality="best" if loss == 0 else "inaccuracy", phase="opening", tags=[],
        clock=None, eval_before_cp=0, eval_after_cp=0,
    )


def test_parse_pgn_indented_headers():
    # Collage Telegram : lignes 2+ indentées (run live 03, partie Dame précoce).
    game = parse_pgn('[White "Test"]\n  [Black "staroflexeur"]\n  1. e4 e5 2. Nf3 *\n')
    assert game.headers["Black"] == "staroflexeur"


def test_select_critical_explosive_is_bonus():
    # 3 a/c remplissent le budget ; la meilleure d s'ajoute en 4e sans rien évincer.
    plies = [_ply(i, 0) for i in range(41)]
    plies[22], plies[26], plies[30] = _ply(22, 12), _ply(26, 0, second_gap=40), _ply(30, 15)
    plies[34], plies[38] = _ply(34, 2), _ply(38, 1)
    explosive = [CriticalPosition(kind="d", ply=plies[34], score=3.0),
                 CriticalPosition(kind="d", ply=plies[38], score=5.0)]
    selected = select_critical(plies, "white", explosive)
    assert [(c.kind, c.ply.ply) for c in selected] == [("a", 22), ("c", 26), ("a", 30), ("d", 38)]


@pytest.mark.parametrize("loss, move_number, retained", [(12, 5, False), (12, 15, True), (25, 5, True)])
def test_select_critical_opening_threshold(loss, move_number, retained):
    # Ouverture assumée : perte ≥ 20 exigée jusqu'au coup 10, ≥ 10 ensuite.
    # Une 2e erreur nette (ply 2) évite le repli « pire coup ».
    plies = [_ply(0, loss, move_number=move_number), _ply(1, 0), _ply(2, 30, move_number=20)]
    selected = select_critical(plies, "white")
    assert [(c.kind, c.ply.ply) for c in selected] == ([("a", 0)] if retained else []) + [("a", 2)]


def test_render_position(tmp_path):
    out = tmp_path / "pos.png"
    fen = "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3"
    assert render_position(fen, "black", "g8f6", str(out)) == str(out)
    with Image.open(out) as image:
        assert image.size == (SIZE, SIZE)


def test_render_position_with_explosive_arrow(tmp_path):
    out = tmp_path / "pos.png"
    fen = "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 3 3"
    render_position(fen, "black", "g8f6", str(out), alt_uci="g7g6")
    with Image.open(out) as image:
        assert image.size == (SIZE, SIZE)
