# aria/chess_coach/summary.py
#
# Fiche structurée d'une partie analysée (sprint 26, tronçon 03).
#
# summarize() produit les métadonnées de la fiche `chess_game` écrite en
# mémoire épisodique par le router : valeurs scalaires uniquement
# (str, int, float, bool, None — contrainte ChromaDB). Les faits bruts par
# demi-coup sont sérialisés en JSON (`plies_json`) pour permettre un
# recalcul futur sans Stockfish (bilan joueur, sprint 27).
#
# summary_text() produit le document indexé : 2-3 phrases françaises.
# Module pur : aucun import mémoire / LLM / exécution.

import json
import math
import statistics

from chess_coach.analysis import GameAnalysis

_OPENING_PLIES = 12
_ERROR_QUALITIES = ("mistake", "blunder")
_QUALITIES = ("best", "correct", "inaccuracy", "mistake", "blunder")
_PHASES = ("opening", "middlegame", "endgame")

_COLOR_FR = {"white": "blancs", "black": "noirs"}
_OUTCOME_FR = {"win": "victoire", "loss": "défaite", "draw": "nulle", "unknown": "issue inconnue"}
_PHASE_FR = {"opening": "ouverture", "middlegame": "milieu", "endgame": "finale"}


def _header(headers: dict, key: str) -> str:
    """Valeur d'en-tête, "" si absente ou inconnue (« ? », « ????.??.?? »)."""
    value = headers.get(key, "")
    return "" if value in ("?", "????.??.??") else value


def _elo(headers: dict, key: str) -> int | None:
    value = _header(headers, key)
    return int(value) if value.isdigit() else None


def _outcome(result: str, nico_color: str) -> str:
    if result == "1/2-1/2":
        return "draw"
    if result in ("1-0", "0-1"):
        nico_won = (result == "1-0") == (nico_color == "white")
        return "win" if nico_won else "loss"
    return "unknown"


def _accuracy(loss: float) -> float:
    """Précision d'un coup (formule Lichess), bornée à [0, 100]."""
    return max(0.0, min(100.0, 103.1668 * math.exp(-0.04354 * loss) - 3.1669))


def _move_accuracy(loss: float) -> float:
    """Précision d'un coup, formule Lichess complète (bonus +1), bornée à [0, 100]."""
    if loss <= 0:
        return 100.0
    return max(0.0, min(100.0, 103.1668100711649 * math.exp(-0.04354415386753951 * loss)
                        - 3.166924740191411 + 1))


def _game_accuracy(plies: list, color: str) -> float | None:
    """Précision de la partie pour color, algorithme Lichess (AccuracyPercent.scala).

    Série des % de gain point de vue blancs sur les N+1 positions ; une
    fenêtre glissante par coup (le début répète la première fenêtre) ; poids
    d'un coup = écart-type (population) de sa fenêtre, borné [0,5 ; 12].
    Précision = (moyenne pondérée + moyenne harmonique) / 2 sur les coups de color.
    """
    if not any(p.color == color for p in plies):
        return None
    series = [p.win_before if p.color == "white" else 100 - p.win_before for p in plies]
    last = plies[-1]
    series.append(last.win_after if last.color == "white" else 100 - last.win_after)
    window = max(2, min(8, (len(series) - 1) // 10))
    windows = [series[:window]] * max(0, min(window, len(series)) - 2)
    windows += [series[i:i + window] for i in range(len(series) - window + 1)]
    weights = [max(0.5, min(12.0, statistics.pstdev(w))) for w in windows]

    pairs = [(_move_accuracy(_effective_loss(p)), w) for p, w in zip(plies, weights) if p.color == color]
    weighted = sum(a * w for a, w in pairs) / sum(w for _, w in pairs)
    # Écart à Lichess : plancher à 1 % par coup, sinon une précision nulle
    # (gaffe totale) rendrait la moyenne harmonique indéfinie.
    harmonic = statistics.harmonic_mean([max(1.0, a) for a, _ in pairs])
    return round((weighted + harmonic) / 2, 1)


def _label(p) -> str:
    """« 39.Bb2 » pour les blancs, « 39...Bb2 » pour les noirs."""
    return f"{p.move_number}{'.' if p.color == 'white' else '...'}{p.san}"


def _effective_loss(p) -> float:
    # Bruit moteur (écart tronçon 01) : le meilleur coup peut afficher une
    # perte légèrement positive d'une position à l'autre. On la ramène à 0
    # pour ne pas pénaliser la précision d'un coup jugé « meilleur ».
    return 0.0 if p.quality == "best" else p.loss


def summarize(analysis: GameAnalysis) -> dict:
    """GameAnalysis → métadonnées scalaires de la fiche `chess_game`."""
    headers = analysis.headers
    color = analysis.nico_color
    plies = analysis.plies
    nico = [p for p in plies if p.color == color]
    opponent = [p for p in plies if p.color != color]
    kinds = {c.ply.ply: c.kind for c in analysis.critical}

    result = _header(headers, "Result")
    outcome = _outcome(result, color)
    opponent_key = "Black" if color == "white" else "White"
    nico_key = "White" if color == "white" else "Black"
    eco_url = _header(headers, "ECOUrl")
    opening = _header(headers, "Opening") or (eco_url.rstrip("/").rsplit("/", 1)[-1] if eco_url else "")

    summary = {
        "date": _header(headers, "Date") or _header(headers, "UTCDate"),
        "nico_color": color,
        "color_source": analysis.color_source,
        "opponent": _header(headers, opponent_key),
        "elo_nico": _elo(headers, nico_key + "Elo"),
        "elo_opponent": _elo(headers, opponent_key + "Elo"),
        "result": result,
        "outcome": outcome,
        "termination": _header(headers, "Termination"),
        "time_control": _header(headers, "TimeControl"),
        "eco": _header(headers, "ECO"),
        "opening": opening,
        "opening_line": " ".join(p.san for p in plies[:_OPENING_PLIES]),
        "n_plies": len(plies),
    }

    for quality in _QUALITIES:
        summary[f"nico_{quality}"] = sum(1 for p in nico if p.quality == quality)

    def first_error(side):
        return next((p.move_number for p in side if p.quality in _ERROR_QUALITIES), None)

    summary["first_error_nico"] = first_error(nico)
    summary["first_error_opponent"] = first_error(opponent)

    for phase in _PHASES:
        losses = [_effective_loss(p) for p in nico if p.phase == phase]
        summary[f"accuracy_{phase}"] = (
            round(sum(_accuracy(loss) for loss in losses) / len(losses), 1) if losses else None
        )

    # Sprint 29 : précision unique de la partie (Lichess) ; accuracy_{phase}
    # gardées pour la compatibilité des fiches, plus affichées.
    summary["accuracy"] = _game_accuracy(plies, color)

    # Pire coup de Nico : plus forte perte, seulement à partir de 10 pts.
    worst = max(nico, key=lambda p: p.loss, default=None)
    if worst is None or worst.loss < 10:
        worst = None
    summary["worst_move"] = _label(worst) if worst else None
    summary["worst_win_before"] = round(worst.win_before, 1) if worst else None
    summary["worst_win_after"] = round(worst.win_after, 1) if worst else None

    # Meilleur coup = coup le plus rare (sprint 29, tronçon 12) : parmi les coups
    # de Nico de perte ≤ 2 dotés d'une probabilité Maia, le moins probable.
    rare = [p for p in nico if p.played_p is not None and p.loss <= 2]
    best = min(rare, key=lambda p: p.played_p, default=None)
    summary["best_move"] = _label(best) if best else None
    summary["best_move_p"] = round(best.played_p, 3) if best else None

    # % de gain de Nico avant chacun de ses coups.
    wins = [p.win_before for p in nico]
    summary["max_win_nico"] = round(max(wins), 1) if wins else None
    summary["min_win_nico"] = round(min(wins), 1) if wins else None
    summary["unconverted"] = bool(wins) and max(wins) >= 80 and outcome != "win"
    summary["saved"] = bool(wins) and min(wins) <= 20 and outcome != "loss"

    # Erreurs adverses (perte ≥ 20) et réponse de Nico au demi-coup suivant.
    punished = 0
    errors = [p for p in opponent if p.loss >= 20]
    for p in errors:
        reply = plies[p.ply + 1] if p.ply + 1 < len(plies) else None
        if reply is not None and reply.loss < 10:
            punished += 1
    summary["opponent_errors"] = len(errors)
    summary["opponent_errors_punished"] = punished

    has_clock = any(p.clock is not None for p in nico)
    summary["errors_low_clock"] = (
        sum(1 for p in nico if p.quality in _ERROR_QUALITIES and p.clock is not None and p.clock < 60)
        if has_clock else None
    )

    summary["plies_json"] = json.dumps([
        {
            "ply": p.ply, "move_number": p.move_number, "color": p.color,
            "san": p.san, "uci": p.uci,
            "win_before": round(p.win_before, 1), "win_after": round(p.win_after, 1),
            "loss": round(p.loss, 1), "best_san": p.best_san, "quality": p.quality,
            "phase": p.phase, "tags": p.tags, "clock": p.clock,
            "kind": kinds.get(p.ply),
            # Sprint 28 : la clé difficulty marque une fiche de la saison 1.
            "difficulty": None if p.difficulty is None else round(p.difficulty),
            "second_gap": None if p.second_gap is None else round(p.second_gap, 1),
            # Sprint 29 : motifs du meilleur coup (absents des fiches antérieures).
            "motifs": p.motifs,
        }
        for p in plies
    ], ensure_ascii=False, separators=(",", ":"))
    return summary


def summary_text(analysis: GameAnalysis, summary: dict) -> str:
    """Document indexé de la fiche : 2-3 phrases françaises."""
    def player(name, elo):
        return f"{name}, {elo}" if elo is not None else name

    nico = player(_COLOR_FR[summary["nico_color"]], summary["elo_nico"])
    opponent = summary["opponent"] or "adversaire inconnu"
    if summary["elo_opponent"] is not None:
        opponent += f" ({summary['elo_opponent']})"
    date = f" du {summary['date']}" if summary["date"] else ""
    opening = " ".join(v for v in (summary["eco"], summary["opening"]) if v) or "inconnue"
    result = summary["result"] or "?"

    sentences = [
        f"Partie d'échecs{date} : Nico ({nico}) contre {opponent}, ouverture {opening}, "
        f"résultat {result} ({_OUTCOME_FR[summary['outcome']]})."
    ]
    accuracies = [
        f"{_PHASE_FR[phase]} {summary[f'accuracy_{phase}']:.0f} %"
        for phase in _PHASES if summary[f"accuracy_{phase}"] is not None
    ]
    if accuracies:
        sentences.append("Précision " + ", ".join(accuracies) + ".")
    errors = (f"{summary['nico_inaccuracy']} imprécision(s), {summary['nico_mistake']} erreur(s), "
              f"{summary['nico_blunder']} gaffe(s)")
    if summary["first_error_nico"] is not None:
        errors += f" ; 1re erreur au coup {summary['first_error_nico']}"
    sentences.append(errors + ".")
    return " ".join(sentences)
