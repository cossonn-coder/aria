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


def _pass(infos, monkeypatch):
    searched = []
    monkeypatch.setattr(live, "_search_position", lambda *args: searched.append(args) or None)
    outcome = analyse_pass(EngineProxy(FakeEngine(infos), 1, lambda: False), chess.STARTING_FEN, 1500, "")
    return outcome, searched


def test_forced_move_detected(monkeypatch):
    outcome, searched = _pass([_info("e2e4", 0), _info("d2d4", -300)], monkeypatch)
    assert outcome == {"result": "none", "explosive": None, "forced": {"uci": "e2e4", "san": "e4"}}
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
