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


@pytest.mark.asyncio
async def test_submit_text_from_thread_goes_through_kernel_and_send(monkeypatch):
    # Sprint 39, tronçon 02 : l'échiquier envoie un PGN comme un message de Nico.
    monkeypatch.setattr(telegram_interface.config, "allowed_user_id", 777)
    kernel = MagicMock()
    kernel.handle_event = AsyncMock(return_value="analyse")
    iface = TelegramInterface(kernel=kernel, token="x")
    iface.app = MagicMock()
    iface.app.bot.send_chat_action = AsyncMock()
    iface.send = AsyncMock()
    iface.loop = asyncio.get_running_loop()

    pgn = '[White "nico"]\n\n1. e4 e5 *'
    assert await asyncio.to_thread(iface.submit_text, pgn) is True
    for _ in range(100):
        if iface.send.await_count:
            break
        await asyncio.sleep(0.01)

    event = kernel.handle_event.await_args.args[0]
    assert event.content == pgn
    assert event.user_id == "777"
    iface.send.assert_awaited_once_with(777, "analyse")


def test_submit_text_without_loop_returns_false():
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    assert iface.submit_text("1. e4 *") is False


# ── Sprint 40 (#131) : filtre utilisateur et métacommandes ──────────────────

def _update_from(user_id, text="bonjour"):
    """Update Telegram minimal : message texte privé de user_id."""
    from datetime import datetime
    from telegram import Chat, Message, Update, User
    user = User(id=user_id, first_name="x", is_bot=False)
    message = Message(
        message_id=1, date=datetime.now(), chat=Chat(id=user_id, type="private"),
        from_user=user, text=text,
    )
    return Update(update_id=1, message=message)


def _command_update(chat_id=42):
    update = MagicMock()
    update.effective_chat.id = chat_id
    return update


def test_text_from_other_user_is_not_handled(monkeypatch):
    # Seul ALLOWED_USER_ID atteint _handle_message (donc le kernel).
    monkeypatch.setattr(telegram_interface.config, "allowed_user_id", 777)
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    iface.app = MagicMock()
    iface._add_handlers()
    text_handler = iface.app.add_handler.call_args_list[0].args[0]

    assert not text_handler.check_update(_update_from(999))
    assert text_handler.check_update(_update_from(777))


@pytest.mark.asyncio
async def test_help_command_lists_commands():
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    iface.app = MagicMock()
    iface.app.bot.send_message = AsyncMock()

    await iface._cmd_help(_command_update(), None)

    text = iface.app.bot.send_message.await_args.kwargs["text"]
    for name in telegram_interface.meta_commands.COMMANDS:
        assert f"/{name}" in text


@pytest.mark.asyncio
async def test_board_https_sends_web_app_button(monkeypatch):
    # Sprint 41 : URL https → bouton Mini App vers l'échiquier.
    url = "https://aria.example.ts.net"
    monkeypatch.setattr(telegram_interface.config, "board_url", url)
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    iface.app = MagicMock()
    iface.app.bot.send_message = AsyncMock()

    await iface._cmd_board(_command_update(), None)

    kwargs = iface.app.bot.send_message.await_args.kwargs
    button = kwargs["reply_markup"].inline_keyboard[0][0]
    assert button.web_app.url == url


@pytest.mark.asyncio
async def test_board_http_sends_plain_link(monkeypatch):
    # Sprint 41 : URL http → lien texte, pas de bouton (refusé par Telegram).
    url = "http://192.168.1.124:5002"
    monkeypatch.setattr(telegram_interface.config, "board_url", url)
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    iface.app = MagicMock()
    iface.app.bot.send_message = AsyncMock()

    await iface._cmd_board(_command_update(), None)

    kwargs = iface.app.bot.send_message.await_args.kwargs
    assert kwargs["text"] == url
    assert "reply_markup" not in kwargs


@pytest.mark.asyncio
async def test_reboot_writes_marker_and_stops(monkeypatch, tmp_path):
    marker = tmp_path / "aria" / "reboot_pending"
    monkeypatch.setattr(telegram_interface, "REBOOT_MARKER", marker)
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    iface.app = MagicMock()
    iface.app.bot.send_message = AsyncMock()

    await iface._cmd_reboot(_command_update(), None)

    assert marker.exists()
    assert iface.restart_requested is True
    iface.app.stop_running.assert_called_once()


@pytest.mark.asyncio
async def test_post_init_with_marker_announces_back(monkeypatch, tmp_path):
    marker = tmp_path / "reboot_pending"
    marker.touch()
    monkeypatch.setattr(telegram_interface, "REBOOT_MARKER", marker)
    monkeypatch.setattr(telegram_interface.config, "allowed_user_id", 777)
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    application = MagicMock()
    application.bot.set_my_commands = AsyncMock()
    application.bot.send_message = AsyncMock()

    await iface._post_init(application)

    application.bot.send_message.assert_awaited_once_with(chat_id=777, text="✅ De retour.")
    assert not marker.exists()
    application.bot.set_my_commands.assert_awaited_once()


@pytest.mark.asyncio
async def test_again_resends_last_kernel_reply():
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    iface.app = MagicMock()
    sent = []
    iface.app.bot.send_message = AsyncMock(side_effect=lambda **kw: sent.append(kw["text"]))

    await iface.send(42, "réponse du kernel")
    await iface._cmd_help(_command_update(), None)
    await iface._cmd_again(_command_update(), None)

    assert sent[-1] == "réponse du kernel"


@pytest.mark.asyncio
async def test_oublie_writes_reset_marker_with_chat_key(monkeypatch):
    written = []
    monkeypatch.setattr(telegram_interface, "write_conversation_reset", written.append)
    iface = TelegramInterface(kernel=MagicMock(), token="x")
    iface.app = MagicMock()
    iface.app.bot.send_message = AsyncMock()

    await iface._cmd_oublie(_command_update(chat_id=42), None)

    assert written == ["42"]
    text = iface.app.bot.send_message.await_args.kwargs["text"]
    assert text == telegram_interface.meta_commands.FORGET_TEXT
