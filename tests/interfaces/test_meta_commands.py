# tests/interfaces/test_meta_commands.py
#
# Sprint 40 (#131) : textes des métacommandes.

import json

from interfaces import meta_commands


def test_help_lists_every_command():
    text = meta_commands.help_text()
    for name, description in meta_commands.COMMANDS.items():
        assert f"/{name} — {description}" in text


def test_board_returns_configured_url(monkeypatch):
    monkeypatch.setattr(meta_commands.config, "board_url", "http://exemple:5002")
    assert meta_commands.board_text() == "http://exemple:5002"


# ── Tronçon 02 : consultations ───────────────────────────────────────────────

from datetime import datetime


def test_logs_count_default_and_cap():
    assert meta_commands.logs_count([]) == 30
    assert meta_commands.logs_count(["50"]) == 50
    assert meta_commands.logs_count(["500"]) == 200


def test_logs_text_joins_lines():
    assert meta_commands.logs_text(["a", "b"]) == "a\nb"


def test_errors_text_keeps_last_warnings_and_errors():
    lines = ["INFO ok", "WARNING w1", "ERROR e1", "Traceback (most recent call last):", "INFO fin"]
    assert meta_commands.errors_text(lines) == "WARNING w1\nERROR e1\nTraceback (most recent call last):"
    assert meta_commands.errors_text(["INFO ok"]) == "Aucune erreur récente."


def test_llm_text_keeps_last_ten_llm_lines():
    lines = [f"[LLM] groq (m) a répondu. {i}" for i in range(12)] + ["INFO autre"]
    text = meta_commands.llm_text(lines)
    assert text.splitlines() == lines[2:12]


def test_intents_text_lists_active_only():
    data = {
        "a": {"name": "échecs", "status": "active", "next_action": "analyser la partie"},
        "b": {"name": "lecture", "status": "active", "next_action": None},
        "c": {"name": "vieux", "status": "completed", "next_action": "x"},
    }
    assert meta_commands.intents_text(data) == "échecs — analyser la partie\nlecture"


def test_parties_text_last_five_newest_first():
    games = [
        {"date": f"2026.10.{i:02d}", "nico_color": "white", "opponent": f"adv{i}",
         "outcome": "win", "opening": "Italienne"}
        for i in range(1, 7)
    ]
    games[-1].update(elo_opponent=1500, nico_color="black", outcome="loss")
    lines = meta_commands.parties_text(games).splitlines()
    assert len(lines) == 5
    assert lines[0] == "2026.10.06 · noirs · contre adv6 (1500) · défaite · Italienne"
    assert lines[-1].startswith("2026.10.02")
    assert meta_commands.parties_text([]) == "Aucune partie enregistrée."


def test_openings_text_format_order_and_unknown_line():
    goring = {"opening": "x", "opening_group": "Göring Gambit", "nico_color": "white"}
    games = [{**goring, "outcome": o} for o in ["win"] * 5 + ["loss"] * 3]
    games += [{"opening": "x", "opening_group": "Dutch Defense", "nico_color": "black", "outcome": "draw"},
              {**goring, "outcome": "unknown"}]

    assert meta_commands.openings_text(games).splitlines() == [
        "Göring Gambit (blancs) : 5 V, 0 N, 3 D — 62 % [8 parties]",
        "Dutch Defense (noirs) : 0 V, 1 N, 0 D — 0 % [1 partie]",
        "Issue inconnue, non comptée : 1 fiche(s)",
    ]
    assert meta_commands.openings_text([]) == meta_commands.NO_OPENINGS


def _opening_game(outcome, color="white", group="Göring Gambit", **extra):
    return {"opening": "x", "opening_group": group, "nico_color": color, "outcome": outcome, **extra}


def _plies(color, **win_by_move):
    """plies_json : un coup de chaque couleur par numéro ; l'adversaire porte un leurre."""
    other = "black" if color == "white" else "white"
    plies = []
    for key, win in win_by_move.items():
        number = int(key[1:])
        plies += [{"color": color, "move_number": number, "win_before": win},
                  {"color": other, "move_number": number, "win_before": 1.0}]
    return json.dumps(plies)


def test_opening_report_full_text():
    games = [
        _opening_game("win", n_plies=40, elo_opponent=1500, plies_json=_plies("white", m10=70.0, m20=90.0)),
        _opening_game("win", n_plies=50, elo_opponent=1601, plies_json=_plies("white", m10=60.0, m20=80.5)),
        _opening_game("draw", n_plies=60, plies_json=_plies("white", m10=50.0)),
        _opening_game("loss", n_plies=30, elo_opponent=1400, plies_json=_plies("white", m10=40.0, m20=30.0)),
        _opening_game("unknown", n_plies=999, elo_opponent=9999),
    ]
    assert meta_commands.opening_report_text(games, "Göring Gambit").splitlines() == [
        "Göring Gambit (blancs) : 2 V, 1 N, 1 D — 50 % [4 parties]",
        "Coups par partie en moyenne : 22,5",
        "Elo adverse moyen : victoires 1550, défaites 1400",
        "% de gain au coup 10 : victoires 65,0, nulles 50,0, défaites 40,0",
        "% de gain au coup 20 : victoires 85,2, défaites 30,0",
    ]


def test_opening_report_recent_games_only_above_five_sorted_by_date():
    # Chargées dans l'ordre d'analyse : la seule défaite a la date de partie la plus ancienne.
    games = [_opening_game("win", date=f"2026.10.0{i}", timestamp=f"2026-11-0{i}") for i in range(2, 6)]
    games.append(_opening_game("loss", date="2026.10.01", timestamp="2026-11-09"))
    assert "dernières" not in meta_commands.opening_report_text(games, "goring")

    games.append(_opening_game("win", timestamp="2026-10-06T10:00:00"))  # sans date : timestamp[:10]
    lines = meta_commands.opening_report_text(games, "goring").splitlines()
    assert lines[0].endswith("[6 parties]")
    assert lines[-1] == "5 dernières : 5 V — 100 %"


def test_opening_report_no_game_at_move_20_omits_line():
    games = [_opening_game("win", plies_json=_plies("white", m10=70.0))]
    text = meta_commands.opening_report_text(games, "goring")
    assert "coup 10" in text
    assert "coup 20" not in text
    # Fiche sans aucune donnée de détail : le bilan seul, au singulier.
    assert meta_commands.opening_report_text([_opening_game("win")], "goring") == (
        "Göring Gambit (blancs) : 1 V — 100 % [1 partie]"
    )


def test_opening_report_query_matching():
    games = [_opening_game("win"), _opening_game("win", group="Danish Gambit"),
             _opening_game("win", group="Gambit"), _opening_game("win", group="Dutch Defense")]
    assert meta_commands.opening_report_text(games, "GORING").startswith("Göring Gambit (blancs)")
    # Égalité exacte : ce groupe seul, même si d'autres le contiennent.
    assert meta_commands.opening_report_text(games, "gambit").startswith("Gambit (blancs)")
    assert meta_commands.opening_report_text(games, "gamb") == (
        "Plusieurs ouvertures correspondent : Danish Gambit, Gambit, Göring Gambit."
    )
    assert meta_commands.opening_report_text(games, "najdorf") == (
        "Aucune ouverture ne correspond à « najdorf ». Liste : /ouvertures"
    )


def test_opening_report_two_colors_two_sections_most_played_first():
    games = [_opening_game("win"), _opening_game("loss", color="black"), _opening_game("draw", color="black")]
    assert meta_commands.opening_report_text(games, "goring") == (
        "Göring Gambit (noirs) : 1 N, 1 D — 0 % [2 parties]\n\nGöring Gambit (blancs) : 1 V — 100 % [1 partie]"
    )


def test_status_text():
    status = {
        "started_at": datetime(2026, 10, 29, 8, 0),
        "now": datetime(2026, 10, 29, 10, 5),
        "commit": "ca132e1",
        "branch": "feat/sprint40-metacommandes",
        "rss_mb": 812,
        "counts": {"aria_episodic": 120, "aria_conversation": 40},
        "quarantine": 3,
    }
    text = meta_commands.status_text(status)
    assert "29/10 08:00 (2 h 05)" in text
    assert "Commit ca132e1 sur feat/sprint40-metacommandes" in text
    assert "812 Mo" in text
    assert "aria_episodic : 120" in text
    assert "Quarantaine : 3 dossier(s)" in text
