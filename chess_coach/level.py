# aria/chess_coach/level.py
#
# Niveau joué (sprint 52, tronçon 01).
#
# Deux mesures solides calculées sur les fiches `chess_game` (dicts de
# métadonnées, comme rendus par `bridge.load_chess_games()`) :
# - la performance Elo (formule classique : Elo moyen des adversaires
#   + 400·log10(p / (1 − p)), terme borné à ±800) ;
# - le rang de la précision d'une partie parmi toutes les parties de Nico.
# Module pur : aucun import mémoire / LLM / moteur.

import math

_OUTCOME_SCORE = {"win": 1.0, "draw": 0.5, "loss": 0.0}
_BOUND = 800


def performance(games: list) -> tuple[int, int] | None:
    """(performance Elo, nombre de parties comptées) ; None si aucune partie comptée.
    Comptée : issue connue (victoire, nulle, défaite) et Elo adverse connu."""
    counted = [g for g in games if g.get("outcome") in _OUTCOME_SCORE and g.get("elo_opponent")]
    if not counted:
        return None
    n = len(counted)
    p = sum(_OUTCOME_SCORE[g["outcome"]] for g in counted) / n
    mean = sum(g["elo_opponent"] for g in counted) / n
    # p = 0 ou 1 : le logarithme diverge, on prend directement la borne.
    if p == 0:
        delta = -_BOUND
    elif p == 1:
        delta = _BOUND
    else:
        delta = max(-_BOUND, min(_BOUND, 400 * math.log10(p / (1 - p))))
    return round(mean + delta), n


def accuracy_rank(accuracy: float, games: list) -> tuple[int, int]:
    """(rang, total) de la précision parmi les fiches qui en ont une.
    Rang = 1 + nombre de fiches à précision strictement supérieure (ex æquo à égalité)."""
    accuracies = [g["accuracy"] for g in games if g.get("accuracy") is not None]
    return 1 + sum(1 for a in accuracies if a > accuracy), len(accuracies)
