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

    # Une seule passe : (fen, meilleur coup) puis (fen, coup joué) (sprint 29, tronçon 12).
    assert len(seen) == 2
    assert plies[1].difficulty == 1307 and plies[1].played_p == 0.5
    assert plies[0].difficulty is None and plies[2].difficulty is None
    assert plies[0].played_p is None and plies[2].played_p is None


@pytest.mark.skipif(not os.path.exists(os.path.join(config.maia_models_dir, "rapid_model.pt")),
                    reason="poids Maia-2 absents")
def test_assign_difficulty_real_maia():
    plies = [_ply(32, 17, "white")]
    difficulty.assign_difficulty(plies, "white", 1307, config.maia_models_dir)
    assert plies[0].difficulty > 1700


@pytest.mark.skipif(not os.path.exists(os.path.join(config.maia_models_dir, "rapid_model.pt")),
                    reason="poids Maia-2 absents")
def test_reply_distribution_real_maia():
    # Sprint 29 : position aux noirs (démiroir) et aux blancs, en un seul lot.
    import chess
    black_fen = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 3 3"
    fens = [black_fen, SPIKE_FEN]
    for fen, replies in zip(fens, difficulty.reply_distribution(fens, 1300, config.maia_models_dir)):
        legal = {m.uci() for m in chess.Board(fen).legal_moves}
        assert replies and all(uci in legal and 0 < p <= 1 for uci, p in replies)
        assert sum(p for _, p in replies) <= 1
