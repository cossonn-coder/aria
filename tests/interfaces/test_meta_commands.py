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
