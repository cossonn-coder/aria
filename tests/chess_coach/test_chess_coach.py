# tests/chess_coach/test_chess_coach.py
#
# Cas nominaux du paquet chess_coach (sprint 26, tronçon 01).

from pathlib import Path

import chess
import pytest
from PIL import Image

from chess_coach.analysis import CriticalPosition, PlyAnalysis, analyze, detect_color, parse_pgn, select_critical
from chess_coach.analysis import clear_advantage
from chess_coach.explosive import _line_sacrifice, find_explosive
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
    # Tronçon 08 : suite coupée au point où l'avantage devient clair.
    assert len(d.explosive.trap_line_san) <= 15
    assert d.explosive.evidence
    assert d.explosive.trap_end_fen


@pytest.mark.skipif(not Path(STOCKFISH).exists(), reason="Stockfish absent")
def test_explosive_excludes_first_pass_best():
    # Tronçon 08 : si la 1re passe donne 8.Nd5 meilleur, ce n'est pas une occasion explosive.
    board = chess.Board()
    for san in ["e4", "c5", "d4", "cxd4", "c3", "dxc3", "Nxc3", "Nc6", "Nf3", "Nf6",
                "Bc4", "e6", "O-O", "a6"]:
        board.push_san(san)
    ply = _ply(14, 0, move_number=8, fen_before=board.fen(), win_before=55.0)
    ply.uci, ply.best_uci = "e4e5", "c3d5"
    found = find_explosive([ply], "white", STOCKFISH)
    assert found == []


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


def _ply(ply, loss, second_gap=None, move_number=None, fen_before=chess.STARTING_FEN, win_before=50.0, pv_uci=()):
    return PlyAnalysis(
        ply=ply, move_number=move_number or ply // 2 + 1, color="white" if ply % 2 == 0 else "black", san="e4", uci="e2e4",
        fen_before=fen_before, win_before=win_before, win_after=win_before - loss, loss=loss,
        best_san="e4", best_uci="e2e4", pv_san=["e4"], second_gap=second_gap,
        quality="best" if loss == 0 else "inaccuracy", phase="opening", tags=[],
        clock=None, eval_before_cp=0, eval_after_cp=0, pv_uci=list(pv_uci),
    )


# Cavalier noir égaré en d4 : 1.e3 a6 2.exd4 gagne une pièce (avantage clair en 3 demi-coups).
HANGING_FEN = "r1bqkbnr/pppppppp/8/8/3n4/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
HANGING_PV = ["e2e3", "a7a6", "e3d4"]


def _line(fen, sans):
    board = chess.Board(fen)
    return [board.push_san(san) for san in sans]


def test_clear_advantage_material():
    board = chess.Board(HANGING_FEN)
    n, criterion = clear_advantage(board, _line(HANGING_FEN, ["e3", "a6", "exd4"]), 50.0, False)
    assert n <= 4 and criterion == "material"


def test_clear_advantage_quiet_line_none():
    sans = ["e4", "e5", "Nf3", "Nc6", "Bc4", "Bc5", "c3", "Nf6", "d3", "d6"]
    assert clear_advantage(chess.Board(), _line(chess.STARTING_FEN, sans), 50.0, False) is None


def test_clear_advantage_after_cap_on_quiet_moves_none():
    # L'avance de développement (Nf3 + Nc3) n'arrive qu'au 11e demi-coup, calme.
    sans = ["a3", "a6", "h3", "h6", "b3", "b6", "g3", "g6", "Nf3", "a5", "Nc3"]
    assert clear_advantage(chess.Board(), _line(chess.STARTING_FEN, sans), 50.0, False) is None


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
    plies[26] = _ply(26, 0, second_gap=40, fen_before=HANGING_FEN, pv_uci=HANGING_PV)
    selected = select_critical(plies, "white", explosive)
    assert [(c.kind, c.ply.ply) for c in selected] == [("a", 22), ("c", 26), ("a", 30), ("d", 38)]


def test_select_critical_empty_without_fallback():
    # Tronçon 08 : plus de repli « pire coup ».
    plies = [_ply(i, 5 if i % 2 == 0 else 0) for i in range(10)]
    assert select_critical(plies, "white") == []


@pytest.mark.parametrize("win_before_error, retained", [(50.0, True), (5.0, False)])
def test_select_critical_turning_point(win_before_error, retained):
    # Erreur adverse ≥ 15 puis coup de Nico à perte < 10 → tournant, sauf partie déjà décidée.
    plies = [_ply(0, 0), _ply(1, 20, win_before=win_before_error),
             _ply(2, 3, fen_before=HANGING_FEN, pv_uci=HANGING_PV)]
    selected = select_critical(plies, "white")
    assert [(c.kind, c.ply.ply) for c in selected] == ([("e", 2)] if retained else [])
    if retained:
        assert selected[0].evidence == "material" and selected[0].line_san == ["e3", "a6", "exd4"]


def test_select_critical_unique_threshold_15():
    plies = [_ply(0, 0, second_gap=16, fen_before=HANGING_FEN, pv_uci=HANGING_PV)]
    assert [(c.kind, c.ply.ply) for c in select_critical(plies, "white")] == [("c", 0)]


@pytest.mark.parametrize("loss, move_number, retained", [(12, 5, False), (12, 15, True), (25, 5, True)])
def test_select_critical_opening_threshold(loss, move_number, retained):
    # Ouverture assumée : perte ≥ 20 exigée jusqu'au coup 10, ≥ 10 ensuite.
    # Une 2e erreur nette (ply 2) garde la sélection non vide dans les deux cas.
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
