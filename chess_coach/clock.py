# aria/chess_coach/clock.py
#
# Temps d'une partie avec horloges (sprint 51, tronçon 03).
#
# Un PGN collé avec ses `%clk` signifie que Nico a peiné à trouver ses coups
# dans le temps : le code calcule le temps passé sur chaque coup, écrit la
# ligne Temps et repère ses 3 réflexions les plus longues (≥ 20 s), chacune
# dotée d'un verdict factuel (écart au 2e coup, perte, difficulté Maia).
# Module pur : fonctions sur des PlyAnalysis, aucun import mémoire / LLM.

_LONG_MIN = 20
_LONG_MAX = 3
# Difficulté Maia relative à l'Elo de Nico : à sa portée / difficile pour son niveau.
_EASY_MARGIN = 100
_HARD_MARGIN = 300


def _base_and_increment(time_control: str | None) -> tuple:
    """« 600 » ou « 600+5 » → (600, 5) ; autre format → (None, incrément ou 0)."""
    base, _, inc = (time_control or "").partition("+")
    increment = int(inc) if inc.isdigit() else 0
    return (int(base) if base.isdigit() else None), increment


def move_times(plies: list, time_control: str | None) -> list:
    """Temps passé sur chaque ply (s) : pendule du camp avant le coup − pendule après
    + incrément. Avant son 1er coup, un camp a la base de la cadence. None sans horloge."""
    base, increment = _base_and_increment(time_control)
    remaining = {"white": base, "black": base}
    times = []
    for p in plies:
        before = remaining[p.color]
        times.append(None if before is None or p.clock is None else before - p.clock + increment)
        remaining[p.color] = p.clock
    return times


def long_thinks(plies: list, times: list, nico_color: str) -> list:
    """Les 3 coups de Nico les plus longs à ≥ 20 s, [(PlyAnalysis, s)], ordre chronologique."""
    found = [(p, t) for p, t in zip(plies, times)
             if p.color == nico_color and t is not None and t >= _LONG_MIN]
    longest = sorted(found, key=lambda pt: -pt[1])[:_LONG_MAX]
    return sorted(longest, key=lambda pt: pt[0].ply)


def verdict(p, elo: int | None) -> str:
    """Verdict d'une réflexion longue : « faits : conclusion », vide si rien à dire."""
    facts = []
    if p.second_gap is not None and p.second_gap < 5:
        facts.append("plusieurs coups gardaient l'avantage")
    elif p.second_gap is not None and p.second_gap >= 15:
        facts.append("un seul coup tenait")
    hard = False
    if p.difficulty is not None:
        maia = f"Maia ≈ {p.difficulty:.0f}"
        if elo is not None and p.difficulty <= elo + _EASY_MARGIN:
            facts.append(f"coup à ta portée ({maia})")
        elif elo is not None and p.difficulty >= elo + _HARD_MARGIN:
            hard = True
            facts.append(f"coup difficile pour ton niveau ({maia})")
        else:
            facts.append(maia)
    conclusion = None
    if p.second_gap is not None and p.second_gap < 5 and p.loss < 10:
        conclusion = "un coup simple suffisait"
    elif (p.second_gap is not None and p.second_gap >= 15) or hard:
        conclusion = "réflexion justifiée"
    text = ", ".join(facts)
    if conclusion:
        text = f"{text} : {conclusion}" if text else conclusion
    return text


def lost_on_time(outcome: str, termination: str | None) -> bool:
    """Défaite au temps, d'après l'en-tête Termination (format anglais ou français)."""
    term = (termination or "").lower()
    return outcome == "loss" and ("on time" in term or "au temps" in term)


def _label(p) -> str:
    return f"{p.move_number}{'.' if p.color == 'white' else '...'}{p.san}"


def _seconds(x: float) -> str:
    """10.94 → « 10,9 s »."""
    return f"{x:.1f}".replace(".", ",") + " s"


def _mmss(x: float) -> str:
    return f"{int(x) // 60}:{int(x) % 60:02d}"


def _mean(values: list) -> float | None:
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _pace(plies: list, times: list, nico_color: str) -> str:
    """« toi 10,9 s par coup, adversaire 7,4 s » (un camp sans temps connu est omis)."""
    nico = _mean([t for p, t in zip(plies, times) if p.color == nico_color])
    opp = _mean([t for p, t in zip(plies, times) if p.color != nico_color])
    parts = []
    if nico is not None:
        parts.append(f"toi {_seconds(nico)} par coup")
    if opp is not None:
        parts.append(f"adversaire {_seconds(opp)}")
    return ", ".join(parts)


def time_line(plies: list, times: list, nico_color: str, period: list | None,
              errors_low_clock: int | None, outcome: str, termination: str | None,
              time_control: str | None) -> str | None:
    """Ligne Temps écrite par le code ; None si la partie n'a aucune horloge."""
    if all(p.clock is None for p in plies):
        return None
    line = f"⏱️ Temps : {_pace(plies, times, nico_color)}."
    if period:
        # Pendules des deux camps avant le 1er coup de Nico de la période gagnante.
        start = plies.index(period[0])
        base, _ = _base_and_increment(time_control)
        clocks = {"white": base, "black": base}
        for p in plies[:start]:
            clocks[p.color] = p.clock
        opp_color = "black" if nico_color == "white" else "white"
        if clocks[nico_color] is not None and clocks[opp_color] is not None:
            line += (f" Dès le coup {period[0].move_number} (début de la période gagnante) : "
                     f"pendules {_mmss(clocks[nico_color])} contre {_mmss(clocks[opp_color])}, "
                     f"puis {_pace(plies[start:], times[start:], nico_color)}.")
    long = [(p, t) for p, t in zip(plies, times)
            if p.color == nico_color and t is not None and t >= _LONG_MIN]
    if long:
        line += " Réflexions de 20 s ou plus : " + ", ".join(f"{_label(p)} {t:.0f} s" for p, t in long) + "."
    if errors_low_clock:
        line += f" Erreurs à moins d'une minute : {errors_low_clock}."
    if lost_on_time(outcome, termination):
        line += " Perdu au temps."
    return line


def long_thinks_text(thinks: list) -> str | None:
    """Coups longs pour la fiche : « 14.Rxb4 54 s, 22.Re1 43 s, 37.Kd3 35 s »."""
    return ", ".join(f"{_label(p)} {t:.0f} s" for p, t in thinks) or None
