# aria/chess_coach/player_model.py
#
# Modèle joueur façon RPG (sprint 28, tronçon 02).
#
# build_profile() rejoue l'historique des fiches `chess_game` de la saison 1
# (fiches dont plies_json porte la clé `difficulty`) et produit le profil :
# classements Elo par thème (façon puzzles), niveaux, badges, inventaire
# d'ouvertures. Rien n'est stocké : le profil est recalculé à chaque analyse.
# Module pur : aucun import mémoire / LLM / exécution.

import json
from dataclasses import dataclass, field

_MIN_PLIES = 20
_DEFAULT_ELO = 1300

# Classements : identifiant → libellé affiché.
LABELS = {
    "global": "Global",
    "hanging": "Gain de matériel",
    # Motifs tactiques (sprint 29) : clés de chess_coach.motifs, détectés sur la
    # PV du meilleur coup. « hangingPiece » alimente « hanging » (continuité des
    # fiches antérieures) ; tous les mats sont regroupés sous « mates ».
    "fork": "Fourchette",
    "pin": "Clouage",
    "skewer": "Enfilade",
    "discoveredAttack": "Attaque à la découverte",
    "doubleCheck": "Échec double",
    "sacrifice": "Sacrifice",
    "trappedPiece": "Pièce enfermée",
    "advancedPawn": "Pion avancé",
    "attackingF2F7": "Attaque sur f2/f7",
    "capturingDefender": "Capture du défenseur",
    "exposedKing": "Roi exposé",
    "attraction": "Attraction",
    "clearance": "Dégagement",
    "collinearMove": "Coup colinéaire",
    "deflection": "Déviation",
    "interference": "Interception",
    "intermezzo": "Coup intermédiaire",
    "xRayAttack": "Rayon X",
    "mates": "Mats",
    "punish": "Punir les erreurs",
    "opening": "Ouverture",
    "convert": "Convertir l'avantage",
    "endgame": "Finale",
    "result": "Résultats",
}

# Nom affiché de chaque mat de chess_coach.motifs (« mate » seul : mat sans motif nommé).
MATE_LABELS = {
    "smotheredMate": "mat étouffé",
    "backRankMate": "mat du couloir",
    "anastasiaMate": "mat d'Anastasia",
    "hookMate": "mat de l'hameçon",
    "arabianMate": "mat arabe",
    "dovetailMate": "mat de Cozio",
    "bodenMate": "mat de Boden",
    "doubleBishopMate": "mat des deux fous",
    "balestraMate": "mat de l'arbalète",
    "cornerMate": "mat du coin",
    "morphysMate": "mat de Morphy",
    "operaMate": "mat de l'opéra",
    "pillsburysMate": "mat de Pillsbury",
    "killBoxMate": "mat de la mise en boîte",
    "vukovicMate": "mat de Vukovic",
    "blindSwineMate": "mat des deux tours",
    "twoRooksMate": "mat des deux tours",
    "epauletteMate": "mat des épaulettes",
    "swallowstailMate": "mat du guéridon",
    "triangleMate": "mat du triangle",
    "mate": "mat",
}

# Classements joués ; « global » = moyenne de ceux qui ont au moins une épreuve.
_THEMES = [key for key in LABELS if key != "global"]

# Épreuve : seuils en points de % de gain.
_TRIAL_MIN_STAKE = 10
_FOUND_MAX_LOSS = 10
_PUNISH_MIN_LOSS = 15
_CONVERT_MIN_WIN = 70
_OPENING_MAX_MOVE = 10
_OPENING_MAX_LOSS = 20

# Facteur K : 16 pour les 30 premières épreuves d'un classement, 8 ensuite ;
# 32 pour le résultat de partie.
_K_EARLY, _K_LATE, _K_EARLY_TRIALS, _K_RESULT = 16, 8, 30, 32

_RESULT_SCORE = {"win": 1.0, "draw": 0.5, "loss": 0.0}
_FAMILY_ENDS = {"Defense", "Game", "Opening", "Gambit", "Attack", "System"}


@dataclass
class Rating:
    value: float
    trials: int = 0

    @property
    def level(self) -> int:
        return int(self.value // 100)


@dataclass
class Trial:
    """Une épreuve et son effet sur un classement."""
    label: str           # « 17.Qb3 », « 17...Qb3 », « coups 1-10 », « résultat »
    difficulty: float
    score: float         # 1 trouvé / gagné, 0 raté / perdu, 0,5 nulle
    delta: float
    mate: str | None = None   # nom du mat (« mat d'Anastasia ») pour une épreuve « mates »


@dataclass
class GameDelta:
    """Effet de la dernière partie sur un classement."""
    delta: float = 0.0
    top: Trial | None = None   # épreuve au |ΔR| max


@dataclass
class OpeningStats:
    wins: int = 0
    draws: int = 0
    losses: int = 0

    @property
    def games(self) -> int:
        return self.wins + self.draws + self.losses

    @property
    def win_rate(self) -> float:
        return self.wins / self.games if self.games else 0.0


@dataclass
class Profile:
    ratings: dict = field(default_factory=dict)      # id → Rating
    last_game: dict = field(default_factory=dict)    # id → GameDelta
    badges: dict = field(default_factory=dict)       # nom → libellé de partie
    openings: dict = field(default_factory=dict)     # (famille, couleur) → OpeningStats
    n_games: int = 0


def opening_family(opening: str) -> str:
    """Slug Chess.com → famille (« Scotch-Game-Goring-… » → « Scotch Game »)."""
    words = [w for w in opening.split("-") if w]
    for i, word in enumerate(words):
        if word in _FAMILY_ENDS:
            return " ".join(words[:i + 1])
    return " ".join(words[:2])


def _move_label(ply: dict) -> str:
    sep = "." if ply["color"] == "white" else "..."
    return f"{ply['move_number']}{sep}{ply['san']}"


def _game_label(game: dict) -> str:
    return f"{game.get('date') or '?'} contre {game.get('opponent') or '?'}"


def _expected(difficulty: float, rating: float) -> float:
    return 1 / (1 + 10 ** ((difficulty - rating) / 400))


def _apply(rating: Rating, difficulty: float, score: float, k: float | None = None) -> float:
    """Met à jour un classement et renvoie ΔR. K par défaut selon l'ancienneté."""
    if k is None:
        k = _K_EARLY if rating.trials < _K_EARLY_TRIALS else _K_LATE
    delta = k * (score - _expected(difficulty, rating.value))
    rating.value += delta
    rating.trials += 1
    return delta


def _record(game_deltas: dict, key: str, trial: Trial) -> None:
    gd = game_deltas[key]
    gd.delta += trial.delta
    if gd.top is None or abs(trial.delta) > abs(gd.top.delta):
        gd.top = trial


def _mean(ratings: dict, start: float) -> float:
    """Moyenne des thèmes ayant ≥ 1 épreuve (anti-dilution) ; aucun → valeur de départ."""
    played = [ratings[key].value for key in _THEMES if ratings[key].trials]
    return sum(played) / len(played) if played else start


def _move_themes(plies: list, i: int) -> list:
    """Thèmes dont relève l'épreuve au demi-coup i (hors global et ouverture)."""
    p = plies[i]
    themes = []
    if "motifs" in p:
        # Fiche sprint 29 : motifs du meilleur coup ; mats regroupés sous « mates ».
        for motif in p["motifs"]:
            key = "hanging" if motif == "hangingPiece" else "mates" if motif in MATE_LABELS else motif
            if key not in themes:
                themes.append(key)
    elif "hanging" in (p.get("tags") or []) or "x" in (p.get("best_san") or ""):
        # Fiches antérieures (sans clé motifs) : règle historique des pièces en prise.
        themes.append("hanging")
    if i > 0 and plies[i - 1]["loss"] >= _PUNISH_MIN_LOSS:
        themes.append("punish")
    if p["win_before"] >= _CONVERT_MIN_WIN:
        themes.append("convert")
    if p.get("phase") == "endgame":
        themes.append("endgame")
    return themes


def _is_trial(p: dict, color: str) -> bool:
    return (
        p["color"] == color
        and p.get("difficulty") is not None
        and _TRIAL_MIN_STAKE <= p["win_before"] <= 100 - _TRIAL_MIN_STAKE
        and (p["loss"] >= _TRIAL_MIN_STAKE or (p.get("second_gap") or 0) >= _TRIAL_MIN_STAKE)
    )


def _season_games(games: list) -> list:
    """Fiches de la saison 1 (clé difficulty) d'au moins 20 demi-coups, avec plies décodés."""
    kept = []
    for game in games:
        plies = json.loads(game.get("plies_json") or "[]")
        if (game.get("n_plies") or 0) >= _MIN_PLIES and plies and "difficulty" in plies[0]:
            kept.append((game, plies))
    return kept


def build_profile(games: list) -> Profile:
    """Rejoue les fiches (ordre reçu) et renvoie le profil RPG de Nico."""
    season = _season_games(games)
    profile = Profile(n_games=len(season))
    if not season:
        return profile

    start = float(season[0][0].get("elo_nico") or _DEFAULT_ELO)
    ratings = {key: Rating(start) for key in LABELS}
    profile.ratings = ratings
    streak_wins = streak_crush = 0
    family_count = {}

    for game, plies in season:
        color = game["nico_color"]
        label = _game_label(game)
        deltas = {key: GameDelta() for key in LABELS}
        unlocked = []
        global_before = ratings["global"].value

        # Ouverture : une épreuve par partie (Maia muette avant le coup 10).
        opening_diff = game.get("elo_opponent") or game.get("elo_nico")
        if opening_diff is not None:
            missed = any(
                p["color"] == color and p["move_number"] <= _OPENING_MAX_MOVE
                and p["loss"] >= _OPENING_MAX_LOSS
                for p in plies
            )
            score = 0.0 if missed else 1.0
            d = _apply(ratings["opening"], opening_diff, score)
            _record(deltas, "opening", Trial("coups 1-10", opening_diff, score, d))
            ratings["global"].value = _mean(ratings, start)

        # Épreuves coup par coup.
        for i, p in enumerate(plies):
            if not _is_trial(p, color):
                continue
            difficulty = p["difficulty"]
            score = 1.0 if p["loss"] < _FOUND_MAX_LOSS else 0.0
            if score and difficulty >= ratings["global"].value + 400:
                unlocked.append("Coup de maître")
            # Nom du mat nommé (« mate » seul n'en a pas), porté par l'épreuve « mates ».
            mate = next((MATE_LABELS[m] for m in p.get("motifs") or []
                         if m in MATE_LABELS and m != "mate"), None)
            for key in _move_themes(plies, i):
                d = _apply(ratings[key], difficulty, score)
                _record(deltas, key, Trial(_move_label(p), difficulty, score, d,
                                           mate if key == "mates" else None))
            # Global tenu à jour pour le seuil de « Coup de maître » de l'épreuve suivante.
            ratings["global"].value = _mean(ratings, start)

        # Résultat de partie contre l'Elo adverse (thème « Résultats »).
        outcome = game.get("outcome")
        elo_opp = game.get("elo_opponent")
        if outcome in _RESULT_SCORE and elo_opp is not None:
            score = _RESULT_SCORE[outcome]
            d = _apply(ratings["result"], elo_opp, score, k=_K_RESULT)
            _record(deltas, "result", Trial("résultat", elo_opp, score, d))

        # Global = moyenne des thèmes ; son delta = moyenne après − moyenne avant.
        ratings["global"].value = _mean(ratings, start)
        deltas["global"].delta = ratings["global"].value - global_before

        # Badges de la partie et des séries.
        win = outcome == "win"
        elo_nico = game.get("elo_nico")
        if win and elo_opp is not None and elo_nico is not None and elo_opp >= elo_nico + 100:
            unlocked.append("Tueur de géant")
        if game.get("nico_blunder") == 0 and game["n_plies"] >= 40:
            unlocked.append("Main propre")
        errors = game.get("opponent_errors") or 0
        if errors >= 2 and game.get("opponent_errors_punished") == errors:
            unlocked.append("Justicier")
        min_win = game.get("min_win_nico")
        if min_win is not None and min_win <= 20 and outcome in ("win", "draw"):
            unlocked.append("Phénix")
        streak_wins = streak_wins + 1 if win else 0
        streak_crush = streak_crush + 1 if win and (game.get("max_win_nico") or 0) >= 80 else 0
        if streak_crush >= 3:
            unlocked.append("Bourreau")
        if streak_wins >= 3:
            unlocked.append("Série")

        # Inventaire d'ouvertures.
        if game.get("opening"):
            family = opening_family(game["opening"])
            family_count[family] = family_count.get(family, 0) + 1
            if family_count[family] >= 5:
                unlocked.append("Répertoire")
            if outcome in _RESULT_SCORE:
                stats = profile.openings.setdefault((family, color), OpeningStats())
                if outcome == "win":
                    stats.wins += 1
                elif outcome == "draw":
                    stats.draws += 1
                else:
                    stats.losses += 1

        for badge in unlocked:
            profile.badges.setdefault(badge, label)
        profile.last_game = deltas

    return profile
