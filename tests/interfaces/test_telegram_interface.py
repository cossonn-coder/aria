# tests/interfaces/test_telegram_interface.py
#
# Sprint 21 (#62) : send() réessaie un envoi Telegram après une erreur
# réseau transitoire au lieu de perdre la réponse.

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.error import TimedOut

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
