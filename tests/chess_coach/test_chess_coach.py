# tests/chess_coach/test_chess_coach.py
#
# Cas nominaux du paquet chess_coach (sprint 26, tronçon 01).

from pathlib import Path

import chess
import pytest
from PIL import Image

from chess_coach.analysis import CriticalPosition, PlyAnalysis, analyze, detect_color, parse_pgn, select_critical
from chess_coach.analysis import clear_advantage
from chess_coach.explosive import ExplosiveMove, _accepted_deficit, _admissible, _expectation, _line_sacrifice
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


@pytest.mark.parametrize("loss, sacrifice, gain, retained", [
    (4.0, 3, 0.0, True),    # ancienne règle sprint 28 : sacrifice dans la fenêtre 5
    (12.0, 0, 6.0, True),   # règle Maia : gain d'espérance ≥ 5, fenêtre 15
    (4.0, 0, 3.0, False),   # ni sacrifice, ni piège, gain < 5
])
def test_explosive_admissible_hybrid(loss, sacrifice, gain, retained):
    # Sprint 29, tronçon 07 : ancienne règle OU gain Maia ≥ 5.
    candidate = ExplosiveMove(
        san="Nd5", uci="c3d5", loss=loss, win_after=43.0, pv_san=[], sacrifice=sacrifice, forcing=[],
        trap_reply_san="exd5", score=0.0, evidence="material", expected=50.0 + gain,
    )
    assert _admissible(candidate, 50.0) is retained


def test_accepted_deficit_gambit():
    # Sprint 36 : Göring 4.c3 dxc3 5.Nxc3 = offre acceptée (1 pion) ; 4.Be2 Nf6 sans prise → 0.
    board = chess.Board()
    for san in ["e4", "e5", "Nf3", "Nc6", "d4", "exd4"]:
        board.push_san(san)
    goring = [chess.Move.from_uci(u) for u in ("c2c3", "d4c3", "b1c3")]
    quiet = [chess.Move.from_uci(u) for u in ("f1e2", "g8f6", "f3d4")]
    assert _accepted_deficit(board, goring, 0) == 1
    assert _accepted_deficit(board, quiet, 0) == 0


@pytest.mark.parametrize("forcing, loss, retained", [
    (["check", "capture"], 0.0, True),   # sacrifice accepté avec échec, sans avantage clair
    ([], 4.0, False),                    # bruit 3...a6 : ni échec ni avantage clair
])
def test_explosive_admissible_accepted_sacrifice(forcing, loss, retained):
    candidate = ExplosiveMove(
        san="Bxf7+", uci="c4f7", loss=loss, win_after=50.0, pv_san=[], sacrifice=0, forcing=forcing,
        trap_reply_san="Kxf7", score=0.0, evidence=None, expected=50.0, accepted=2,
    )
    assert _admissible(candidate, 50.0) is retained


def test_expectation_renormalized():
    # Probabilités gardées (somme 0,8) renormalisées : (0,6 × 70 + 0,2 × 30) / 0,8 = 60.
    assert _expectation([{"p": 0.6, "win": 70.0}, {"p": 0.2, "win": 30.0}]) == pytest.approx(60.0)


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
    # 3 a/c remplissent le budget ; jusqu'à 3 d s'ajoutent sans rien évincer,
    # meilleur score d'abord : la plus faible des 4 est écartée.
    plies = [_ply(i, 0) for i in range(41)]
    plies[22], plies[26], plies[30] = _ply(22, 12), _ply(26, 0, second_gap=40), _ply(30, 15)
    for i in (32, 34, 36, 38):
        plies[i] = _ply(i, 2)
    explosive = [CriticalPosition(kind="d", ply=plies[32], score=12.0),
                 CriticalPosition(kind="d", ply=plies[34], score=11.0),
                 CriticalPosition(kind="d", ply=plies[36], score=20.0),
                 CriticalPosition(kind="d", ply=plies[38], score=15.0)]
    plies[26] = _ply(26, 0, second_gap=40, fen_before=HANGING_FEN, pv_uci=HANGING_PV)
    selected = select_critical(plies, "white", explosive)
    assert [(c.kind, c.ply.ply) for c in selected] == [
        ("a", 22), ("c", 26), ("a", 30), ("d", 32), ("d", 36), ("d", 38)]


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
