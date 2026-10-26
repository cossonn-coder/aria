# Tests de l'analyse live de l'échiquier ARIA (sprint 35, tronçon 01) : faux moteur.

import chess
import chess.engine
import pytest

from chess_coach import live
from chess_coach.live import EngineProxy, Superseded, analyse_pass


def _info(move: str, cp: int) -> dict:
    return {"pv": [chess.Move.from_uci(move)], "score": chess.engine.PovScore(chess.engine.Cp(cp), chess.WHITE)}


class FakeEngine:
    """Rend toujours les mêmes infos et note les temps demandés."""

    def __init__(self, infos):
        self.infos = infos
        self.times = []

    def analyse(self, board, limit, **kwargs):
        self.times.append(limit.time)
        return self.infos


def test_proxy_multiplies_time():
    engine = FakeEngine([])
    EngineProxy(engine, 4, lambda: False).analyse(chess.Board(), chess.engine.Limit(time=0.5))
    assert engine.times == [2.0]


def test_proxy_raises_when_stale():
    engine = FakeEngine([])
    with pytest.raises(Superseded):
        EngineProxy(engine, 1, lambda: True).analyse(chess.Board(), chess.engine.Limit(time=0.5))
    assert engine.times == []


def _no_maia(monkeypatch, values=None, replies=None):
    """Maia monkeypatché : pronostic (fen → %) et réponses (fen → [(uci, p)]), 50 % / aucune par défaut."""
    values, replies = values or {}, replies or {}
    monkeypatch.setattr(live, "position_values", lambda fens, *a: [values.get(f, 50) for f in fens])
    monkeypatch.setattr(live, "reply_distribution", lambda fens, *a: [replies.get(f, []) for f in fens])


def _pass(infos, monkeypatch):
    searched = []
    _no_maia(monkeypatch)
    monkeypatch.setattr(live, "_search_position", lambda *args: searched.append(args) or None)
    outcome = analyse_pass(EngineProxy(FakeEngine(infos), 1, lambda: False), chess.STARTING_FEN, 1500, "")
    return outcome, searched


def test_forced_move_detected(monkeypatch):
    outcome, searched = _pass([_info("e2e4", 0), _info("d2d4", -300)], monkeypatch)
    assert outcome == {"result": "none", "explosive": None, "forced": {"uci": "e2e4", "san": "e4"},
                       "best": {"uci": "e2e4", "san": "e4", "pv_san": ["e4"]}, "trap": None,
                       "strategy": {"uci": "e2e4", "san": "e4", "value": 50, "best_value": 50,
                                    "pv_san": ["e4"]}}
    assert len(searched) == 1


def test_no_forced_move_when_gap_small(monkeypatch):
    outcome, _ = _pass([_info("e2e4", 0), _info("d2d4", -20)], monkeypatch)
    assert outcome["forced"] is None


def test_decided_skips_explosive_search(monkeypatch):
    outcome, searched = _pass([_info("e2e4", 1000), _info("d2d4", 990)], monkeypatch)
    assert outcome["result"] == "decided"
    assert searched == []


def test_game_over():
    # Mat du berger : noirs au trait, partie terminée.
    fen = "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
    outcome = analyse_pass(EngineProxy(FakeEngine([]), 1, lambda: False), fen, 1500, "")
    assert outcome["result"] == "game_over"


def _after(move: str) -> str:
    board = chess.Board()
    board.push_uci(move)
    return board.fen()


class RootEngine(FakeEngine):
    """MultiPV de racine fixe ; sous root_moves, score par coup (points de vue du trait)."""

    def __init__(self, infos, scores):
        super().__init__(infos)
        self.scores = scores

    def analyse(self, board, limit, root_moves=None, **kwargs):
        if root_moves is None:
            return self.infos
        return [_info(move.uci(), self.scores[move.uci()]) for move in root_moves]


def test_trap_and_strategy(monkeypatch):
    # d4 : 30 % des réponses humaines (Cf6, −600 pour les noirs) rapportent ≥ +15 pts ;
    # Cf3 : meilleur pronostic Maia (80 % contre 50 % pour e4, le meilleur coup).
    _no_maia(monkeypatch, values={_after("g1f3"): 20},
             replies={_after("d2d4"): [("d7d5", 0.6), ("g8f6", 0.3)], _after("e2e4"): [("e7e5", 0.9)]})
    monkeypatch.setattr(live, "_search_position", lambda *args: None)
    engine = RootEngine([_info("e2e4", 0), _info("d2d4", -20), _info("g1f3", -30)],
                        {"d7d5": 0, "g8f6": -600, "e7e5": 0})
    outcome = analyse_pass(EngineProxy(engine, 1, lambda: False), chess.STARTING_FEN, 1500, "")
    assert outcome["trap"]["uci"] == "d2d4"
    assert outcome["trap"]["p"] == 0.3
    assert [r["san"] for r in outcome["trap"]["replies"]] == ["Nf6"]
    assert outcome["strategy"]["uci"] == "g1f3"
    assert (outcome["strategy"]["value"], outcome["strategy"]["best_value"]) == (80, 50)
