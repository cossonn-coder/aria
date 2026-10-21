# tests/chess_coach/test_player_model.py
#
# Modèle joueur (sprint 28, tronçon 02) : fiches factices en dicts, pas de palace.

import json

from chess_coach.player_model import build_profile


def _ply(ply, color, *, loss=0.0, win_before=50.0, difficulty=None, second_gap=None):
    return {
        "ply": ply, "move_number": ply // 2 + 1, "color": color, "san": "Nf3",
        "win_before": win_before, "loss": loss, "best_san": "Nf3", "tags": [],
        "phase": "middlegame", "difficulty": difficulty, "second_gap": second_gap,
    }


def _game(trial=None, *, outcome="unknown", elo_nico=1300, elo_opponent=None,
          opening="", n_plies=30, with_difficulty=True, opponent="X"):
    """Partie de 30 demi-coups calmes ; `trial` = (difficulty, loss) au demi-coup 24 (blancs,
    thème « Gain de matériel » par la règle des fiches sans clé motifs)."""
    plies = [_ply(i, "white" if i % 2 == 0 else "black") for i in range(n_plies)]
    if trial is not None:
        difficulty, loss = trial
        plies[24].update(difficulty=difficulty, loss=loss, second_gap=20.0, tags=["hanging"])
    if not with_difficulty:
        for p in plies:
            del p["difficulty"]
    return {
        "nico_color": "white", "outcome": outcome, "elo_nico": elo_nico,
        "elo_opponent": elo_opponent, "opening": opening, "n_plies": n_plies,
        "opponent": opponent, "date": "2026.10.19", "nico_blunder": 1,
        "opponent_errors": 0, "opponent_errors_punished": 0,
        "min_win_nico": 50.0, "max_win_nico": 50.0, "plies_json": json.dumps(plies),
    }


def _global(**kwargs):
    return build_profile([_game(**kwargs)]).ratings["global"].value


def _move_delta(trial):
    # Effet de l'épreuve sur son classement (départ 1300).
    return build_profile([_game(trial=trial)]).ratings["hanging"].value - 1300


def test_trial_gain_scales_with_difficulty():
    assert _move_delta((1500, 0.0)) > _move_delta((1000, 0.0)) > 0
    assert _move_delta((1000, 30.0)) < _move_delta((1500, 30.0)) < 0


def test_ignores_pre_season_and_short_games():
    profile = build_profile([
        _game((1500, 0.0), with_difficulty=False),
        _game(n_plies=18),
    ])
    assert profile.n_games == 0
    assert profile.ratings == {}


def test_loss_against_weaker_costs_more():
    # Effet isolé du résultat : écart avec la même partie à issue inconnue.
    def result_delta(elo):
        return _global(outcome="loss", elo_opponent=elo) - _global(elo_opponent=elo)
    assert result_delta(1100) < result_delta(1500) < 0


def test_giant_slayer_unlocked_once():
    profile = build_profile([
        _game(outcome="win", elo_opponent=1450, opponent="A"),
        _game(outcome="win", elo_opponent=1500, opponent="B"),
    ])
    assert profile.badges["Tueur de géant"] == "2026.10.19 contre A"


def test_opening_inventory_win_rate():
    slug = "Scotch-Game-Goring-Double-Pawn-Gambit"
    profile = build_profile([
        _game(outcome="win", opening=slug),
        _game(outcome="loss", opening=slug),
    ])
    stats = profile.openings[("Scotch Game", "white")]
    assert (stats.wins, stats.losses, stats.win_rate) == (1, 1, 0.5)


def test_loss_only_lowers_result_and_global():
    profile = build_profile([_game(outcome="loss", elo_opponent=1300, opening="")])
    # Ouverture réussie (+8, K 16) et défaite à égalité (−16, K 32) : le Global baisse.
    assert profile.ratings["result"].value < 1300
    assert profile.last_game["global"].delta < 0
    assert profile.last_game["global"].top is None


def test_found_move_raises_theme_and_global_is_mean():
    # Fiche sans clé motifs : règle historique (tag hanging) ; Global = moyenne
    # des seuls thèmes joués (gain de matériel + ouverture).
    profile = build_profile([_game((1500, 0.0))])
    r = profile.ratings
    assert r["hanging"].value > 1300
    assert r["result"].value == r["punish"].value == r["fork"].value == 1300
    assert r["global"].value == (r["hanging"].value + r["opening"].value) / 2


def test_motif_fork_found_raises_fork():
    # Fiche sprint 29 : la clé motifs remplace la règle du tag hanging.
    game = _game((1500, 0.0))
    plies = json.loads(game["plies_json"])
    for p in plies:
        p["motifs"] = []
    plies[24]["motifs"] = ["fork", "anastasiaMate"]
    game["plies_json"] = json.dumps(plies)
    profile = build_profile([game])
    r = profile.ratings
    assert r["fork"].value > 1300 and r["mates"].value > 1300
    assert r["hanging"].trials == 0
    assert profile.last_game["mates"].top.mate == "mat d'Anastasia"
    assert r["global"].value == (r["fork"].value + r["mates"].value + r["opening"].value) / 3
