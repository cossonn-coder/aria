# Tests du module niveau joué (sprint 52, tronçon 01).
from chess_coach.level import accuracy_rank, performance


def test_performance_two_wins_one_loss():
    games = [{"outcome": "win", "elo_opponent": 1500}, {"outcome": "win", "elo_opponent": 1500},
             {"outcome": "loss", "elo_opponent": 1500}]
    assert performance(games) == (1620, 3)


def test_performance_all_wins_bounded():
    games = [{"outcome": "win", "elo_opponent": 1400}, {"outcome": "win", "elo_opponent": 1600}]
    assert performance(games) == (2300, 2)


def test_performance_ignores_unknown_and_empty():
    games = [{"outcome": "draw", "elo_opponent": 1500}, {"outcome": "win", "elo_opponent": None},
             {"outcome": "unknown", "elo_opponent": 1500}]
    assert performance(games) == (1500, 1)
    assert performance([]) is None


def test_accuracy_rank_ties_and_missing():
    games = [{"accuracy": 90.0}, {"accuracy": 84.0}, {"accuracy": 84.0}, {"accuracy": None}, {}]
    assert accuracy_rank(84.0, games) == (2, 3)
    assert accuracy_rank(95.0, games) == (1, 3)
