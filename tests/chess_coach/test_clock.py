# tests/chess_coach/test_clock.py
#
# Temps d'une partie avec horloges (sprint 51, tronçon 03) : temps par coup,
# réflexions longues, verdict et ligne Temps écrits par le code.

from chess_coach.analysis import PlyAnalysis
from chess_coach.clock import long_thinks, move_times, time_line, verdict

_FEN = "8/8/8/4k3/8/8/1P6/4K3 w - - 0 1"


def _ply(ply, clock, second_gap=None, loss=0.0, difficulty=None):
    return PlyAnalysis(
        ply=ply, move_number=ply // 2 + 1, color="white" if ply % 2 == 0 else "black", san="b3",
        uci="b2b3", fen_before=_FEN, win_before=50.0, win_after=50.0, loss=loss, best_san="b3",
        best_uci="b2b3", pv_san=["b3"], second_gap=second_gap, quality="best", phase="endgame",
        tags=[], clock=clock, eval_before_cp=0, eval_after_cp=0, difficulty=difficulty,
    )


def test_move_times_from_base():
    plies = [_ply(0, 590), _ply(1, 595), _ply(2, 560), _ply(3, 593)]
    assert move_times(plies, "600") == [10, 5, 30, 2]
    assert move_times(plies, "600+5") == [15, 10, 35, 7]


def test_three_longest_in_order():
    clocks = [570, 600, 545, 600, 535, 600, 495, 600]   # Nico : 30, 25, 10, 40 s
    plies = [_ply(i, c) for i, c in enumerate(clocks)]
    plies.append(_ply(8, 474))                            # 21 s
    thinks = long_thinks(plies, move_times(plies, "600"), "white")
    assert [(p.ply, t) for p, t in thinks] == [(0, 30), (2, 25), (6, 40)]


def test_verdicts():
    assert verdict(_ply(0, 1, second_gap=2, loss=3, difficulty=1350), 1300) == (
        "plusieurs coups gardaient l'avantage, coup à ta portée (Maia ≈ 1350) : un coup simple suffisait")
    assert verdict(_ply(0, 1, second_gap=20, loss=0), None) == "un seul coup tenait : réflexion justifiée"


def test_time_line_lost_on_time():
    plies = [_ply(0, 570), _ply(1, 590), _ply(2, 560), _ply(3, 585)]
    line = time_line(plies, move_times(plies, "600"), "white", None, None, "loss",
                     "dusha28 a gagné au temps", "600")
    assert line == ("⏱️ Temps : toi 20,0 s par coup, adversaire 7,5 s. "
                    "Réflexions de 20 s ou plus : 1.b3 30 s. Perdu au temps.")
