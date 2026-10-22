# tests/chess_coach/test_summary.py
#
# Tests de chess_coach.summary (sprint 26, tronçon 03) — GameAnalysis
# construit à la main, pas de Stockfish.

import json

from chess_coach.analysis import CriticalPosition, GameAnalysis, PlyAnalysis
from chess_coach.summary import summarize, summary_text


def _ply(ply, move_number, color, san, uci, quality, loss, win_before, clock):
    return PlyAnalysis(
        ply=ply, move_number=move_number, color=color, san=san, uci=uci,
        fen_before="8/8/8/8/8/8/8/8 w - - 0 1", win_before=win_before,
        win_after=win_before - loss, loss=loss, best_san=san, best_uci=uci,
        pv_san=[san], second_gap=None, quality=quality, phase="opening",
        tags=[], clock=clock, eval_before_cp=0, eval_after_cp=0,
    )


def test_summarize_nominal():
    plies = [
        _ply(0, 1, "white", "e4", "e2e4", "best", 0.0, 50.0, 600.0),
        # Bruit moteur : perte légèrement positive sur un « meilleur » coup.
        _ply(1, 1, "black", "f5", "f7f5", "best", 1.5, 50.0, 600.0),
        _ply(2, 2, "white", "Qh5+", "d1h5", "mistake", 25.0, 55.0, 590.0),
        _ply(3, 2, "black", "g6", "g7g6", "blunder", 35.0, 75.0, 50.0),
    ]
    plies[3].difficulty, plies[3].second_gap = 1523.4, 17.26
    analysis = GameAnalysis(
        headers={"White": "Ami", "Black": "staroflexeur", "BlackElo": "1307",
                 "WhiteElo": "1272", "Result": "0-1", "Date": "2026.10.19",
                 "ECO": "A80", "ECOUrl": "https://www.chess.com/openings/Dutch-Defense"},
        nico_color="black", color_source="header", plies=plies,
        critical=[CriticalPosition(kind="b", ply=plies[3], score=35.0)],
    )

    s = summarize(analysis)

    assert all(v is None or isinstance(v, (str, int, float, bool)) for v in s.values())
    assert s["outcome"] == "win"
    assert s["opponent"] == "Ami" and s["elo_nico"] == 1307 and s["elo_opponent"] == 1272
    assert s["opening"] == "Dutch-Defense"
    assert s["opening_line"] == "e4 f5 Qh5+ g6"
    assert (s["nico_best"], s["nico_blunder"], s["nico_mistake"]) == (1, 1, 0)
    assert s["first_error_nico"] == 2 and s["first_error_opponent"] == 2
    assert s["accuracy_middlegame"] is None
    assert s["opponent_errors"] == 1 and s["opponent_errors_punished"] == 0
    assert s["errors_low_clock"] == 1
    assert s["unconverted"] is False and s["saved"] is False
    plies_back = json.loads(s["plies_json"])
    assert len(plies_back) == 4 and plies_back[3]["kind"] == "b" and plies_back[0]["kind"] is None
    # Sprint 28 : difficulté (Elo entier) et écart au 2e coup, None par défaut.
    assert plies_back[0]["difficulty"] is None and plies_back[0]["second_gap"] is None
    assert plies_back[3]["difficulty"] == 1523 and plies_back[3]["second_gap"] == 17.3

    text = summary_text(analysis, s)
    assert "Nico (noirs, 1307) contre Ami (1272)" in text and "victoire" in text


def test_accuracy_lichess_and_worst_move():
    # Nico (blancs) : 9 coups propres (perte 2) et une gaffe de 80 pts au coup 9.
    plies = []
    for i in range(20):
        white, blunder = i % 2 == 0, i == 16
        loss = 80.0 if blunder else 2.0
        win_before = 90.0 if blunder else (50.0 if white else 52.0)
        plies.append(_ply(i, i // 2 + 1, "white" if white else "black", "Bb2" if blunder else "a3",
                          "a2a3", "blunder" if blunder else "correct", loss, win_before, None))
    analysis = GameAnalysis(headers={}, nico_color="white", color_source="header", plies=plies)

    s = summarize(analysis)

    arithmetic = sum(min(100, 103.1668 * 2.718281828 ** (-0.04354 * p.loss) - 3.1669)
                     for p in plies if p.color == "white") / 10
    # La gaffe pèse bien plus que dans la moyenne arithmétique (≈ 88 %).
    assert s["accuracy"] < arithmetic - 15
    assert s["worst_move"] == "9.Bb2"
    assert (s["worst_win_before"], s["worst_win_after"]) == (90.0, 10.0)
    assert s["best_move"] is None and s["best_move_p"] is None


def test_best_move_is_rarest_played_move():
    # Trois coups de Nico : banal (p 0,6), rare et bon (p 0,1, perte 1), plus rare mais perdant (p 0,05, perte 8).
    plies = []
    for i, (played_p, loss) in enumerate([(0.6, 0.0), (0.1, 1.0), (0.05, 8.0)]):
        nico = _ply(2 * i, 11 + i, "white", f"N{'abc'[i]}3", "b1c3", "correct", loss, 50.0, None)
        nico.played_p = played_p
        plies += [nico, _ply(2 * i + 1, 11 + i, "black", "a6", "a7a6", "correct", 0.0, 50.0, None)]
    analysis = GameAnalysis(headers={}, nico_color="white", color_source="header", plies=plies)

    s = summarize(analysis)

    assert s["best_move"] == "12.Nb3"
    assert s["best_move_p"] == 0.1
