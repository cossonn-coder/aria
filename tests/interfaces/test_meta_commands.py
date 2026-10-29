# tests/interfaces/test_meta_commands.py
#
# Sprint 40 (#131) : textes des métacommandes.

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
