# tests/chess_coach/test_difficulty.py
#
# Tests de chess_coach.difficulty (sprint 28, tronçon 01) : formule et
# filtrage avec Maia remplacé par des probabilités factices, puis un test
# réel sur la position du spike (sauté si les poids sont absents).

import os

import pytest

from chess_coach import difficulty
from chess_coach.analysis import PlyAnalysis
from config import config

SPIKE_FEN = "r6r/pQp1n1p1/3qbk1p/3nN3/8/8/PP3PPP/RNB1R1K1 w - - 2 17"


def _ply(ply, move_number, color, fen=SPIKE_FEN, best_uci="b7b3"):
    return PlyAnalysis(
        ply=ply, move_number=move_number, color=color, san="?", uci=best_uci,
        fen_before=fen, win_before=50.0, win_after=50.0, loss=0.0, best_san="?",
        best_uci=best_uci, pv_san=[], second_gap=None, quality="best",
        phase="middlegame", tags=[], clock=None, eval_before_cp=0, eval_after_cp=0,
    )


def test_assign_difficulty_formula_and_filter(monkeypatch):
    seen = []

    def fake_probabilities(positions, elo, models_dir):
        seen.extend(positions)
        return [0.5] * len(positions)

    monkeypatch.setattr(difficulty, "_probabilities", fake_probabilities)
    plies = [_ply(8, 5, "white"), _ply(32, 17, "white"), _ply(33, 17, "black")]

    difficulty.assign_difficulty(plies, "white", 1307, "unused")

    assert len(seen) == 1
    assert plies[1].difficulty == 1307
    assert plies[0].difficulty is None and plies[2].difficulty is None


@pytest.mark.skipif(not os.path.exists(os.path.join(config.maia_models_dir, "rapid_model.pt")),
                    reason="poids Maia-2 absents")
def test_assign_difficulty_real_maia():
    plies = [_ply(32, 17, "white")]
    difficulty.assign_difficulty(plies, "white", 1307, config.maia_models_dir)
    assert plies[0].difficulty > 1700
