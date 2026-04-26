# aria/interfaces/telegram_interface.py
#
# Interface Telegram d'ARIA.
#
# Responsabilité : transformer les events Telegram en Event typés,
# appeler kernel.handle_event(), et envoyer la réponse.
#
# Ce module ne contient aucune logique métier.
# Il sait lire les types Telegram (texte, photo) et envoyer
# les réponses appropriées (texte, photo).
#
# Gestion de la concurrence : un Lock par user_id évite les
# réponses entrelacées si l'utilisateur envoie plusieurs messages rapides.

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)

from collections import defaultdict
import asyncio
from pathlib import Path

from config import config
from interfaces.base_interface import BaseInterface
from core.event import Event, EventType


class TelegramInterface(BaseInterface):

    def __init__(self, kernel, token: str):
        super().__init__(kernel)
        self.token = token
        # Un lock par user_id — sérialise les messages d'un même utilisateur
        self.user_locks = defaultdict(asyncio.Lock)

    def start(self):
        self.app = ApplicationBuilder().token(self.token).build()

        # Messages texte
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        # Photos envoyées par l'utilisateur
        self.app.add_handler(
            MessageHandler(filters.PHOTO, self._handle_photo)
        )

        self.app.run_polling()

    # =========================================================
    # HANDLERS ENTRANTS
    # =========================================================

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reçoit un message texte, crée un Event TEXT, attend la réponse."""

        user_id = str(update.effective_user.id)
        chat_id = update.effective_chat.id

        async with self.user_locks[user_id]:
            event = Event.create(
                event_type=EventType.TEXT,
                user_id=user_id,
                content=update.message.text,
                metadata={"chat_id": chat_id},
            )
            result = await self.kernel.handle_event(event)

        await self.send(chat_id, result)

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Reçoit une photo Telegram, télécharge le fichier, crée un Event IMAGE.

        photo[-1] = résolution maximale disponible.
        La caption éventuelle (texte accompagnant la photo) est transmise
        dans le content pour que le router vision puisse l'utiliser.
        """

        user_id = str(update.effective_user.id)
        chat_id = update.effective_chat.id

        async with self.user_locks[user_id]:
            photo = update.message.photo[-1]
            file = await photo.get_file()

            # Téléchargement dans received_images/ — pas à la racine du projet
            image_receive_dir = Path(config.image_receive_dir)
            image_receive_dir.mkdir(parents=True, exist_ok=True)
            dest = image_receive_dir / f"{file.file_id}.jpg"
            file_path = await file.download_to_drive(custom_path=dest)

            event = Event.create(
                event_type=EventType.IMAGE,
                user_id=user_id,
                content={
                    "file_path": str(file_path),
                    "caption": update.message.caption,
                },
                metadata={"chat_id": chat_id},
            )
            result = await self.kernel.handle_event(event)

        await self.send(chat_id, result)

    # =========================================================
    # ENVOI SORTANT
    # =========================================================

    async def send(self, chat_id: int, message):
        """
        Envoie la réponse du kernel à l'utilisateur Telegram.

        Gère trois cas :
        - dict {"type": "image", "path": ..., "caption": ...}
            → send_photo() avec le fichier local
        - dict générique
            → extraction du champ "text" ou str()
        - str
            → send_message() direct
        """

        # ── Résultat image ───────────────────────────────────────────────────
        if isinstance(message, dict) and message.get("type") == "image":
            path = message.get("path", "")
            caption = message.get("caption", "") or ""

            if path and Path(path).exists():
                with open(path, "rb") as photo:
                    await self.app.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=caption[:1024] if caption else None,
                    )
                return

            # Fichier introuvable — on envoie le path en texte (debug)
            await self.app.bot.send_message(
                chat_id=chat_id,
                text=f"Image générée mais fichier introuvable : {path}",
            )
            return

        # ── Résultat texte ───────────────────────────────────────────────────
        if isinstance(message, dict):
            text = message.get("text") or str(message)
        else:
            text = str(message)

        # Telegram limite à 4096 caractères par message
        # On découpe proprement sans couper au milieu d'un mot
        MAX = 4096
        chunks = [text[i:i+MAX] for i in range(0, len(text), MAX)]
        for chunk in chunks:
            await self.app.bot.send_message(
                chat_id=chat_id,
                text=chunk,
            )