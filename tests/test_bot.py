# Test du point d'entrée : sortie immédiate après l'arrêt de l'interface.

import importlib

import pytest

import logger


@pytest.mark.parametrize("restart_requested, exit_code", [(False, 0), (True, 1)])
def test_main_exits_immediately_after_start(monkeypatch, restart_requested, exit_code):
    # Sprint 40 : code 1 après /reboot, pour que systemd relance.
    # configure_root(force=True) remplacerait les handlers de pytest à l'import.
    monkeypatch.setattr(logger, "configure_root", lambda level="INFO": None)
    bot = importlib.import_module("bot")

    calls = []

    class FakeTelegram:
        def __init__(self, kernel, token):
            self.restart_requested = restart_requested

        def start(self):
            calls.append("start")

        def submit_text(self, text):
            return False

    monkeypatch.setenv("ARIA_BOT_TOKEN", "x")
    monkeypatch.setattr(bot, "AriaKernel", lambda: object())
    monkeypatch.setattr(bot, "TelegramInterface", FakeTelegram)
    # Le serveur de l'échiquier lierait un port réel.
    monkeypatch.setattr(bot, "start_board_server", lambda submit_text: calls.append("board"))
    monkeypatch.setattr(bot.logging, "shutdown", lambda: calls.append("shutdown"))
    monkeypatch.setattr(bot.os, "_exit", lambda code: calls.append(("exit", code)))

    bot.main()

    assert calls == ["board", "start", "shutdown", ("exit", exit_code)]
