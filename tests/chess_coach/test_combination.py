# tests/chess_coach/test_combination.py
#
# Pointe d'une combinaison et défenses réfutées (sprint 61, tronçon 01).

from types import SimpleNamespace

import chess

from chess_coach import analysis, difficulty
from chess_coach.analysis import CriticalPosition
from chess_coach.combination import point_of

# Cas de référence (audit sprint 61 §1) : Nico blancs, 12.Qxe7+ … 14.Ba3 cloue Nb4 sur Ke7.
FEN = "r1b1k2r/1pq1bppp/p4n2/3p4/1n1P4/3B1N2/2P1QPPP/RNB1R1K1 w kq - 0 12"
LINE = ["Qxe7+", "Qxe7", "Rxe7+", "Kxe7", "Ba3", "Be6", "Bxb4+", "Kd7"]


def test_point_of_reference_case():
    assert point_of(FEN, LINE, "white") == {
        "gain": 6, "won": "Nb4", "prep": 4, "pin": ("Nb4", "Ke7"), "brought": 3, "defender": (0, "Be7"),
    }


class _FakeEngine:
    """Réfutation de ...a5 par Bxb4+ Kd8 ; après la reprise axb4, Nico répond Rxa8."""

    def analyse(self, board, limit, root_moves=None, multipv=None):
        if root_moves:
            return [{"pv": [chess.Move.from_uci(u) for u in ("a6a5", "a3b4", "e7d8")]}]
        return {"pv": [chess.Move.from_uci("a1a8")]}


def test_assign_defenses_records_refutation_and_recapture(monkeypatch):
    # Maia simulé : a5 retenu, Be6 (coup de la ligne moteur) écarté.
    monkeypatch.setattr(difficulty, "reply_distribution",
                        lambda fens, elo, models_dir: [[("a6a5", 0.93), ("c8e6", 0.03)]])
    monkeypatch.setattr(analysis, "run_on_engines",
                        lambda path, work, items: [work(_FakeEngine(), item) for item in items])
    ply = SimpleNamespace(fen_before=FEN, color="white")
    error = CriticalPosition(kind="a", ply=ply, score=20.0, best_line_san=LINE)

    analysis.assign_defenses([error], "unused", 1711, "unused")

    assert error.point["prep"] == 4
    assert error.defenses == [{"san": "a5", "p": 0.93, "line_san": ["a5", "Bxb4+", "Kd8"],
                               "recapture": ("axb4", "Rxa8")}]
