# tests/interfaces/test_telegram_interface.py
#
# Sprint 21 (#62) : send() réessaie un envoi Telegram après une erreur
# réseau transitoire au lieu de perdre la réponse.
# Sprint 30 : signal d'attente (#103), photo en échec sautée (#104).

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.error import TimedOut

from interfaces import telegram_interface
from interfaces.telegram_interface import TelegramInterface


@pytest.mark.asyncio
async def test_send_text_retries_after_timeout():
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    iface.app = MagicMock()
    # Premier appel : timeout réseau ; second : succès.
    iface.app.bot.send_message = AsyncMock(side_effect=[TimedOut(), None])

    with patch("interfaces.telegram_interface.asyncio.sleep", new=AsyncMock()) as sleep:
        await iface.send(42, "bonjour")

    assert iface.app.bot.send_message.await_count == 2
    sleep.assert_awaited_once_with(2)


@pytest.mark.asyncio
async def test_send_images_text_sends_photos_then_text(tmp_path):
    # Sprint 26 : images_text → une photo par image, puis le texte.
    paths = []
    for i in range(2):
        p = tmp_path / f"pos{i}.png"
        p.write_bytes(b"png")
        paths.append(str(p))
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    iface.app = MagicMock()
    calls = []
    iface.app.bot.send_photo = AsyncMock(side_effect=lambda **kw: calls.append("photo"))
    iface.app.bot.send_message = AsyncMock(side_effect=lambda **kw: calls.append("text"))

    await iface.send(42, {
        "type": "images_text",
        "images": [{"path": p, "caption": "Position"} for p in paths],
        "text": "explication",
    })

    assert calls == ["photo", "photo", "text"]


@pytest.mark.asyncio
async def test_send_failure_is_kept_and_delivered_before_next_reply():
    # Sprint 29 : réessais épuisés → pas d'exception, réponse mise en attente,
    # puis livrée (après avertissement) avant la réponse suivante.
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    iface.app = MagicMock()
    iface.app.bot.send_message = AsyncMock(side_effect=[TimedOut()] * 3)

    with patch("interfaces.telegram_interface.asyncio.sleep", new=AsyncMock()):
        await iface.send(42, "perdue")

    sent = []
    iface.app.bot.send_message = AsyncMock(side_effect=lambda **kw: sent.append(kw["text"]))
    await iface.send(42, "courante")

    assert sent == [
        "⚠️ Ma réponse précédente n'avait pas pu partir :",
        "perdue",
        "courante",
    ]


# ── Sprint 30 (#103) : signal d'attente pendant le traitement ────────────────

def _waiting_iface(delay):
    """Interface dont le kernel met `delay` secondes à répondre."""
    async def slow_handle_event(event):
        await asyncio.sleep(delay)
        return "réponse"
    kernel = MagicMock()
    kernel.handle_event = slow_handle_event
    iface = TelegramInterface(kernel=kernel, token="x")
    iface.app = MagicMock()
    iface.app.bot.send_chat_action = AsyncMock()
    iface.app.bot.send_message = AsyncMock()
    return iface


@pytest.mark.asyncio
async def test_long_processing_sends_wait_notice_once(monkeypatch):
    monkeypatch.setattr(telegram_interface, "TYPING_REFRESH_SECONDS", 0.01)
    monkeypatch.setattr(telegram_interface, "WAIT_NOTICE_SECONDS", 0.05)
    iface = _waiting_iface(0.2)

    result = await iface._handle_with_waiting(42, event=MagicMock())
    await asyncio.sleep(0.1)  # aucune tâche d'attente ne survit à la réponse

    assert result == "réponse"
    assert iface.app.bot.send_chat_action.await_count >= 1
    iface.app.bot.send_message.assert_awaited_once_with(
        chat_id=42, text=telegram_interface.WAIT_NOTICE,
    )


@pytest.mark.asyncio
async def test_short_processing_sends_no_wait_notice(monkeypatch):
    monkeypatch.setattr(telegram_interface, "TYPING_REFRESH_SECONDS", 0.01)
    monkeypatch.setattr(telegram_interface, "WAIT_NOTICE_SECONDS", 0.05)
    iface = _waiting_iface(0.01)

    await iface._handle_with_waiting(42, event=MagicMock())
    await asyncio.sleep(0.1)

    iface.app.bot.send_message.assert_not_awaited()


# ── Sprint 30 (#104) : photo en échec définitif sautée ───────────────────────

@pytest.mark.asyncio
async def test_images_text_failed_photo_is_skipped_text_still_sent(tmp_path):
    p = tmp_path / "pos.png"
    p.write_bytes(b"png")
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    iface.app = MagicMock()
    iface.app.bot.send_photo = AsyncMock(side_effect=TimedOut())
    iface.app.bot.send_message = AsyncMock()

    with patch("interfaces.telegram_interface.asyncio.sleep", new=AsyncMock()):
        await iface.send(42, {
            "type": "images_text",
            "images": [{"path": str(p), "caption": "Position"}],
            "text": "explication",
        })

    iface.app.bot.send_message.assert_awaited_once_with(chat_id=42, text="explication")
