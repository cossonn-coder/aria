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


def test_parties_text_all_games_of_the_day_with_stats():
    # 6 parties du jour (plus de 5), les deux formats de date, une fiche sans date, une d'hier.
    game = {"nico_color": "white", "outcome": "win", "opening": "Italian Game"}
    games = [{**game, "date": "2026.11.03", "opponent": "hier"}]
    games += [{**game, "date": "2026.11.04", "opponent": f"adv{i}"} for i in range(1, 5)]
    games.append({**game, "date": "", "timestamp": "2026-11-04T09:00:00+00:00", "opponent": "sans_date"})
    games.append({**game, "date": "2026-11-04", "opponent": "adv6", "elo_opponent": 1500,
                  "nico_color": "black", "outcome": "loss", "opening": "Dutch Defense"})
    assert meta_commands.parties_text(games, today="2026-11-04").splitlines() == [
        "blancs · contre adv1 · victoire · Italian Game",
        "blancs · contre adv2 · victoire · Italian Game",
        "blancs · contre adv3 · victoire · Italian Game",
        "blancs · contre adv4 · victoire · Italian Game",
        "blancs · contre sans_date · victoire · Italian Game",
        "noirs · contre adv6 (1500) · défaite · Dutch Defense",
        "",
        "Italian Game (blancs) : 5 V, 0 N, 0 D — 100 % [5 parties]",
        "Dutch Defense (noirs) : 0 V, 0 N, 1 D — 0 % [1 partie]",
        "",
        "Aujourd'hui : 5 V, 1 D — 83 % · performance 700 [1 partie]",
    ]
    assert meta_commands.parties_text(games, today="2026-11-05") == "Aucune partie aujourd'hui."


def test_parties_opening_text_report_of_the_day_only():
    game = {"nico_color": "black", "opening": "Scandinavian Defense", "opponent": "adv"}
    games = [{**game, "date": "2026.11.03", "outcome": "loss"},
             {**game, "date": "2026.11.04", "outcome": "win"},
             {**game, "date": "2026.11.04", "outcome": "loss", "opening": "Italian Game"}]
    assert meta_commands.parties_opening_text(games, "scandinavian", today="2026-11-04") == (
        "Scandinavian Defense (noirs) : 1 V — 100 % [1 partie]")
    assert meta_commands.parties_opening_text(games, "scandinavian", today="2026-11-05") == (
        "Aucune partie aujourd'hui.")


def test_openings_text_format_order_and_unknown_line():
    goring = {"opening": "x", "opening_group": "Göring Gambit", "nico_color": "white"}
    games = [{**goring, "outcome": o} for o in ["win"] * 5 + ["loss"] * 3]
    games += [{"opening": "x", "opening_group": "Dutch Defense", "nico_color": "black", "outcome": "draw"},
              {**goring, "outcome": "unknown"}]

    assert meta_commands.openings_text(games).splitlines() == [
        "Dutch Defense (noirs) : 0 V, 1 N, 0 D — 0 % [1 partie]",
        "Göring Gambit (blancs) : 5 V, 0 N, 3 D — 62 % [8 parties]",
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
        "Coups par partie en moyenne : 22,5",
        "Elo adverse moyen : victoires 1550, défaites 1400",
        "% de gain au coup 10 : victoires 65,0, nulles 50,0, défaites 40,0",
        "% de gain au coup 20 : victoires 85,2, défaites 30,0",
        "Göring Gambit (blancs) : 2 V, 1 N, 1 D — 50 % [4 parties]",
        "Performance : 1621 [3 parties]",
    ]


def test_opening_report_recent_games_only_above_five_sorted_by_date():
    # Chargées dans l'ordre d'analyse : la seule défaite a la date de partie la plus ancienne.
    games = [_opening_game("win", date=f"2026.10.0{i}", timestamp=f"2026-11-0{i}") for i in range(2, 6)]
    games.append(_opening_game("loss", date="2026.10.01", timestamp="2026-11-09"))
    assert "dernières" not in meta_commands.opening_report_text(games, "goring")

    games.append(_opening_game("win", timestamp="2026-10-06T10:00:00"))  # sans date : timestamp[:10]
    lines = meta_commands.opening_report_text(games, "goring").splitlines()
    assert lines[-1].endswith("[6 parties]")
    assert lines[-2] == "5 dernières : 5 V — 100 %"


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


def test_opening_report_two_colors_two_sections_most_played_last():
    games = [_opening_game("win"), _opening_game("loss", color="black"), _opening_game("draw", color="black")]
    assert meta_commands.opening_report_text(games, "goring") == (
        "Göring Gambit (blancs) : 1 V — 100 % [1 partie]\n\nGöring Gambit (noirs) : 1 N, 1 D — 0 % [2 parties]"
    )


def test_performance_line_with_last_five():
    # 6 parties à Elo adverse 1500 : la plus ancienne (date) est la seule défaite.
    games = [_opening_game("win", elo_opponent=1500, date=f"2026.10.0{i}") for i in range(2, 7)]
    games.append(_opening_game("loss", elo_opponent=1500, date="2026.10.01"))
    lines = meta_commands.opening_report_text(games, "goring").splitlines()
    assert lines[-1] == "Performance : 1780 [6 parties] · 5 dernières : 2300"
    assert meta_commands.openings_text(games).splitlines()[-1] == lines[-1]


# ── Sprint 53 : périodes et classement par précision ─────────────────────────

def test_parse_period_args():
    assert meta_commands.parse_period_args(["goring", "week"]) == ("goring", "week")
    assert meta_commands.parse_period_args(["month"]) == ("", "month")
    assert meta_commands.parse_period_args(["goring"]) == ("goring", None)
    assert meta_commands.parse_period_args(["Année"]) == ("", "year")


def test_parties_text_week_stats_only_and_period_bilan():
    game = {"nico_color": "white", "outcome": "win", "opening": "Italian Game", "opponent": "adv"}
    games = [{**game, "date": "2026.10.28"},  # hors fenêtre (8 jours avant)
             {**game, "date": "2026.10.29"}, {**game, "date": "2026.11.04", "outcome": "loss"}]
    assert meta_commands.parties_text(games, today="2026-11-04", period="week").splitlines() == [
        "Italian Game (blancs) : 1 V, 0 N, 1 D — 50 % [2 parties]",
        "",
        "7 derniers jours : 1 V, 1 D — 50 %",
    ]
    assert meta_commands.parties_text(games, today="2026-12-31", period="week") == (
        "Aucune partie sur les 7 derniers jours.")


def test_ranking_seven_games_best_five_then_worst_two_above_bilan():
    games = [_opening_game("win", accuracy=float(a), opponent=f"adv{a}", date="2026.11.04")
             for a in (70, 95, 60, 80, 90, 85, 75)]
    games.append(_opening_game("loss", opponent="sans_precision", date="2026.11.04"))
    lines = meta_commands.parties_text(games, today="2026-11-04", period="week").splitlines()
    start = lines.index("🏆 5 meilleures :")
    assert lines[start:] == [
        "🏆 5 meilleures :",
        "95 % · Göring Gambit (blancs) · contre adv95 · victoire · 2026-11-04",
        "90 % · Göring Gambit (blancs) · contre adv90 · victoire · 2026-11-04",
        "85 % · Göring Gambit (blancs) · contre adv85 · victoire · 2026-11-04",
        "80 % · Göring Gambit (blancs) · contre adv80 · victoire · 2026-11-04",
        "75 % · Göring Gambit (blancs) · contre adv75 · victoire · 2026-11-04",
        "📉 5 pires :",
        "60 % · Göring Gambit (blancs) · contre adv60 · victoire · 2026-11-04",
        "70 % · Göring Gambit (blancs) · contre adv70 · victoire · 2026-11-04",
        "",
        "7 derniers jours : 7 V, 1 D — 88 %",
    ]


def test_ranking_three_games_single_list_above_color_sections():
    games = [_opening_game("win", accuracy=91.6, opponent="a", elo_opponent=1340, date="2026.11.06"),
             _opening_game("loss", accuracy=55.0, opponent="b", date="2026.11.05"),
             _opening_game("draw", color="black", accuracy=70.0, opponent="c", date="2026.11.05")]
    blocks = meta_commands.opening_report_text(games, "goring").split("\n\n")
    assert blocks[0].splitlines() == [
        "Par précision :",
        "92 % · Göring Gambit (blancs) · contre a (1340) · victoire · 2026-11-06",
        "70 % · Göring Gambit (noirs) · contre c · nulle · 2026-11-05",
        "55 % · Göring Gambit (blancs) · contre b · défaite · 2026-11-05",
    ]
    assert blocks[1].startswith("Göring Gambit (noirs)")
    assert "Göring Gambit (blancs) : 1 V, 1 D" in blocks[-1]


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


# ── Sprint 56, tronçon 02 : /issue ───────────────────────────────────────────

def test_issue_picks_latest_game_and_computes_result():
    games = [
        {"id": "a", "opponent": "Tailor4321", "date": "2026.11.10", "nico_color": "white"},
        {"id": "b", "opponent": "tailor4321", "date": "2026.11.11", "nico_color": "black"},
        {"id": "c", "opponent": "Autre", "date": "2026.11.12", "nico_color": "white"},
    ]
    opponent, outcome = meta_commands.parse_issue_args(["TAILOR4321", "Victoire"])
    game = meta_commands.latest_game_against(games, opponent)
    assert game["id"] == "b"
    assert (outcome, meta_commands.result_for(outcome, game["nico_color"])) == ("win", "0-1")
    assert meta_commands.parse_issue_args(["x", "Défaite"])[1] == "loss"
    assert meta_commands.issue_text(game, outcome) == "✅ Issue corrigée : contre tailor4321 (2026-11-11) → victoire."


def test_issue_no_game_and_bad_args():
    assert meta_commands.latest_game_against([], "Inconnu") is None
    assert meta_commands.no_game_against_text("Inconnu") == "Aucune partie contre Inconnu."
    assert meta_commands.parse_issue_args(["Tailor4321"]) is None
    assert meta_commands.parse_issue_args(["Tailor4321", "gain"]) is None


# ── /consigne, /consignes (sprint 56, tronçon 04) ────────────────────────────

def test_consigne_args_and_texts():
    assert meta_commands.parse_consigne_args(["retire", "2"]) == ("remove", "2")
    assert meta_commands.parse_consigne_args(["réponds", "court"]) == ("add", "réponds court")
    assert meta_commands.parse_consigne_args([]) is None
    assert meta_commands.consigne_added_text(3, "réponds court") == "📌 Consigne 3 enregistrée : réponds court"
    assert meta_commands.consigne_removed_text(2, "x") == "🗑️ Consigne 2 retirée : x"
    assert meta_commands.no_consigne_text("9") == "Pas de consigne 9. Liste : /consignes"
    assert meta_commands.consignes_text([{"text": "a"}, {"text": "b"}]) == "1. a\n2. b"
    assert meta_commands.consignes_text([]) == "Aucune consigne."
