# Test du point d'entrée : sortie immédiate après l'arrêt de l'interface.

import importlib

import logger


def test_main_exits_immediately_after_start(monkeypatch):
    # configure_root(force=True) remplacerait les handlers de pytest à l'import.
    monkeypatch.setattr(logger, "configure_root", lambda level="INFO": None)
    bot = importlib.import_module("bot")

    calls = []

    class FakeTelegram:
        def __init__(self, kernel, token):
            pass

        def start(self):
            calls.append("start")

    monkeypatch.setenv("ARIA_BOT_TOKEN", "x")
    monkeypatch.setattr(bot, "AriaKernel", lambda: object())
    monkeypatch.setattr(bot, "TelegramInterface", FakeTelegram)
    monkeypatch.setattr(bot.logging, "shutdown", lambda: calls.append("shutdown"))
    monkeypatch.setattr(bot.os, "_exit", lambda code: calls.append(("exit", code)))

    bot.main()

    assert calls == ["start", "shutdown", ("exit", 0)]
