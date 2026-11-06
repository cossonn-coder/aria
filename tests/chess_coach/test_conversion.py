# tests/chess_coach/test_conversion.py
#
# Conversion d'une position gagnante (sprint 51, tronçon 02) : période gagnante,
# idée répétée non jouée, ligne écrite par le code.

from chess_coach.analysis import PlyAnalysis
from chess_coach.conversion import conversion_line, repeated_ideas, winning_period

# Finale : roi blanc e1, pion b2 ; roi noir e5. Nico joue les blancs.
_FEN = "8/8/8/4k3/8/8/1P6/4K3 w - - 0 1"


def _ply(ply, color, san, best_san, best_uci, win_before):
    return PlyAnalysis(
        ply=ply, move_number=ply // 2 + 1, color=color, san=san, uci="b2b3", fen_before=_FEN,
        win_before=win_before, win_after=win_before, loss=0.0, best_san=best_san, best_uci=best_uci,
        pv_san=[best_san], second_gap=None, quality="correct", phase="endgame", tags=[],
        clock=None, eval_before_cp=0, eval_after_cp=0,
    )


def conversion_plies() -> list:
    """Coups 1 à 12 de Nico à 85 % ; Kd2 proposé aux coups 3, 4, 6, joué au 8."""
    plies = []
    for i in range(12):
        move = i + 1
        if move in (3, 4, 6):
            nico = _ply(2 * i, "white", "b3", "Kd2", "e1d2", 85.0)
        elif move == 8:
            nico = _ply(2 * i, "white", "Kd2", "Kd2", "e1d2", 85.0)
        else:
            nico = _ply(2 * i, "white", "b3", "b3", "b2b3", 85.0)
        plies += [nico, _ply(2 * i + 1, "black", "Ke6", "Ke6", "e5e6", 15.0)]
    return plies


def test_conversion_period_and_repeated_king_idea():
    plies = conversion_plies()
    period = winning_period(plies, "white", "loss")
    assert len(period) == 12
    ideas = repeated_ideas(period, plies)
    assert [(i.san, i.moves, i.played_at, i.concept) for i in ideas] == [
        ("Kd2", [3, 4, 6], 8, "activer le roi")]
    assert conversion_line(period, ideas) == (
        "🔄 Conversion : 12 coups à 80 % ou plus (coups 1 à 12) sans gagner. Idées du moteur non "
        "jouées : activer le roi (Kd2, proposé aux coups 3, 4, 6, joué au 8).")
    assert winning_period(plies, "white", "win") is None
