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

from telegram import BotCommand, Update
from telegram.constants import ChatAction
from telegram.error import NetworkError, TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from collections import defaultdict
import asyncio
from pathlib import Path

from config import config
from interfaces import meta_commands
from interfaces.base_interface import BaseInterface
from core.event import Event, EventType
from logger import get_logger

log = get_logger(__name__)

# Retry des envois sur erreur réseau : 3 tentatives, attentes 2 s puis 4 s.
# Doublon possible si Telegram a reçu le message mais que la réponse s'est
# perdue en route — accepté (sprint 21, Q3).
SEND_ATTEMPTS = 3
SEND_BACKOFF_SECONDS = (2, 4)

# Préfixe de la réponse non livrée, renvoyée avant la réponse suivante (sprint 29).
UNDELIVERED_NOTICE = "⚠️ Ma réponse précédente n'avait pas pu partir :"

# Signal d'attente pendant le traitement (sprint 30, #103) : indicateur
# « écrit… » renvoyé toutes les 4 s (Telegram l'efface après 5 s), et un
# seul message d'attente si le traitement dépasse 20 s (sprint 31, #111).
TYPING_REFRESH_SECONDS = 4
WAIT_NOTICE_SECONDS = 20
WAIT_NOTICE = "⏳ Je travaille dessus, ça peut prendre jusqu'à 2 minutes."

# Marqueur posé par /reboot, lu au démarrage suivant pour annoncer le retour
# (sprint 40). Constante module : surchargée en test.
REBOOT_MARKER = Path.home() / ".aria" / "reboot_pending"


def _log_external_failure(future):
    """Journalise l'exception d'un traitement lancé par submit_text."""
    exc = future.exception()
    if exc is not None:
        log.error("telegram_external failed: %s", type(exc).__name__, exc_info=exc)


class TelegramInterface(BaseInterface):

    def __init__(self, kernel, token: str):
        super().__init__(kernel)
        self.token = token
        # Un lock par user_id — sérialise les messages d'un même utilisateur
        self.user_locks = defaultdict(asyncio.Lock)
        # Dernière réponse non livrée par chat_id, en RAM (perdue au
        # redémarrage, accepté). Livrée avant la réponse suivante.
        self.undelivered = {}
        # Boucle asyncio de PTB, connue une fois start() lancé (sprint 39) :
        # submit_text s'en sert pour traiter un texte venu d'un autre thread.
        self.loop = None
        # Dernière réponse du kernel livrée, par chat_id, en RAM : /again la
        # renvoie (sprint 40). Les sorties de métacommandes n'y passent pas.
        self.last_reply = {}
        # Posé par /reboot : bot.py sort alors en code 1, systemd relance.
        self.restart_requested = False

    def start(self):
        self.app = ApplicationBuilder().token(self.token).post_init(self._post_init).build()
        self._add_handlers()

        # Erreurs non rattrapées (getUpdates en échec, envoi définitivement
        # échoué) : une ligne WARNING au lieu d'une trace ERROR complète.
        self.app.add_error_handler(self._on_error)

        # Retries de bootstrap infinis : PTB réessaie indéfiniment l'initialisation
        # (get_me) au lieu de lever et de tuer le process au démarrage.
        self.app.run_polling(bootstrap_retries=-1)

    def _add_handlers(self):
        """Branche messages, photos et métacommandes, filtrés sur Nico seul."""
        # Le bot n'est pas public : tout autre compte est ignoré (sprint 40).
        only_nico = filters.User(user_id=config.allowed_user_id)

        # Messages texte
        self.app.add_handler(
            MessageHandler(only_nico & filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        # Photos envoyées par l'utilisateur
        self.app.add_handler(
            MessageHandler(only_nico & filters.PHOTO, self._handle_photo)
        )

        # Métacommandes : une méthode _cmd_<nom> par entrée de COMMANDS.
        for name in meta_commands.COMMANDS:
            self.app.add_handler(
                CommandHandler(name, getattr(self, f"_cmd_{name}"), filters=only_nico)
            )

    async def _post_init(self, application):
        """
        post_init PTB : boucle mémorisée, commandes déclarées à Telegram,
        annonce du retour si le démarrage fait suite à un /reboot.
        """
        await self._remember_loop(application)
        await application.bot.set_my_commands(
            [BotCommand(name, description) for name, description in meta_commands.COMMANDS.items()]
        )
        if REBOOT_MARKER.exists():
            await application.bot.send_message(
                chat_id=config.allowed_user_id, text=meta_commands.BACK_TEXT,
            )
            REBOOT_MARKER.unlink()
            log.info("meta_reboot back")

    async def _remember_loop(self, application):
        """post_init PTB : mémorise la boucle qui fait tourner le bot."""
        self.loop = asyncio.get_running_loop()

    async def _on_error(self, update, context: ContextTypes.DEFAULT_TYPE):
        """Error handler PTB : journalise l'erreur en une ligne, sans trace."""
        err = context.error
        log.warning("telegram error: %s: %s", type(err).__name__, err)

    # =========================================================
    # HANDLERS ENTRANTS
    # =========================================================

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reçoit un message texte, crée un Event TEXT, attend la réponse."""

        # Trace de réception — sert à diagnostiquer un éventuel double
        # traitement d'un même update (#63).
        log.info(
            "telegram_update update_id=%s message_id=%s type=text",
            update.update_id, update.message.message_id,
        )

        await self._process_text(str(update.effective_user.id), update.effective_chat.id, update.message.text)

    async def _process_text(self, user_id: str, chat_id: int, text: str):
        """Traite un texte de l'utilisateur : kernel sous verrou, puis envoi de la réponse."""
        async with self.user_locks[user_id]:
            event = Event.create(
                event_type=EventType.TEXT,
                user_id=user_id,
                content=text,
                metadata={"chat_id": chat_id},
            )
            result = await self._handle_with_waiting(chat_id, event)

        await self.send(chat_id, result)

    # =========================================================
    # ENTRÉE EXTERNE (échiquier, sprint 39)
    # =========================================================

    def submit_text(self, text: str) -> bool:
        """
        Fait traiter un texte comme un message de Nico, depuis un autre thread.

        Même chemin qu'un message Telegram (verrou, kernel, envoi) dans le chat
        privé de Nico (chat_id = user_id = ALLOWED_USER_ID). N'attend pas la
        fin du traitement. False si la boucle PTB n'est pas encore lancée.
        """
        log.info("telegram_external source=board chars=%d", len(text))
        if self.loop is None:
            return False
        chat_id = config.allowed_user_id
        future = asyncio.run_coroutine_threadsafe(
            self._process_text(str(chat_id), chat_id, text), self.loop,
        )
        # Sans ce callback, une exception du traitement resterait dans le future, muette.
        future.add_done_callback(_log_external_failure)
        return True

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Reçoit une photo Telegram, télécharge le fichier, crée un Event IMAGE.

        photo[-1] = résolution maximale disponible.
        La caption éventuelle (texte accompagnant la photo) est transmise
        dans le content pour que le router vision puisse l'utiliser.
        """

        # Trace de réception (#63), cf. _handle_message.
        log.info(
            "telegram_update update_id=%s message_id=%s type=photo",
            update.update_id, update.message.message_id,
        )

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
            result = await self._handle_with_waiting(chat_id, event)

        await self.send(chat_id, result)

    # =========================================================
    # MÉTACOMMANDES (sprint 40)
    # =========================================================
    # Hors kernel et hors historique : réponse livrée par _deliver, sans
    # toucher last_reply (/again ne renvoie jamais une sortie de commande).

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        log.info("meta_command name=help")
        await self._deliver(update.effective_chat.id, meta_commands.help_text())

    async def _cmd_board(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        log.info("meta_command name=board")
        await self._deliver(update.effective_chat.id, meta_commands.board_text())

    async def _cmd_again(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        log.info("meta_command name=again")
        chat_id = update.effective_chat.id
        await self._deliver(chat_id, self.last_reply.get(chat_id, meta_commands.NOTHING_TO_RESEND))

    async def _cmd_reboot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Réponse, marqueur, arrêt du polling. bot.py sort ensuite en code 1
        et systemd (Restart=on-failure) relance le service.
        """
        log.info("meta_command name=reboot")
        await self._deliver(update.effective_chat.id, meta_commands.REBOOT_TEXT)
        REBOOT_MARKER.parent.mkdir(parents=True, exist_ok=True)
        REBOOT_MARKER.touch()
        self.restart_requested = True
        log.info("meta_reboot requested")
        self.app.stop_running()

    # =========================================================
    # SIGNAL D'ATTENTE
    # =========================================================

    async def _handle_with_waiting(self, chat_id: int, event: Event):
        """
        Appelle le kernel en tenant l'utilisateur informé de l'attente.

        Deux tâches tournent pendant le traitement : l'indicateur « écrit… »
        renouvelé, et le message d'attente unique après WAIT_NOTICE_SECONDS.
        Elles sont annulées dès que le kernel rend la main (réponse ou
        exception), avant l'envoi de la réponse.
        """
        waiting = [
            asyncio.create_task(self._keep_typing(chat_id)),
            asyncio.create_task(self._notice_after_delay(chat_id)),
        ]
        try:
            return await self.kernel.handle_event(event)
        finally:
            for task in waiting:
                task.cancel()
            await asyncio.gather(*waiting, return_exceptions=True)

    async def _keep_typing(self, chat_id: int):
        """Renvoie l'indicateur « écrit… » jusqu'à annulation."""
        while True:
            try:
                await self.app.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            except TelegramError as e:
                log.warning("telegram typing indicator failed: %s, chat_id=%s", type(e).__name__, chat_id)
            await asyncio.sleep(TYPING_REFRESH_SECONDS)

    async def _notice_after_delay(self, chat_id: int):
        """Envoie le message d'attente une seule fois, si le traitement dure."""
        await asyncio.sleep(WAIT_NOTICE_SECONDS)
        try:
            await self.app.bot.send_message(chat_id=chat_id, text=WAIT_NOTICE)
        except TelegramError as e:
            log.warning("telegram wait notice failed: %s, chat_id=%s", type(e).__name__, chat_id)

    # =========================================================
    # ENVOI SORTANT
    # =========================================================

    async def _send_with_retry(self, chat_id: int, make_call):
        """
        Exécute un envoi Telegram, réessayé sur NetworkError (TimedOut inclus).

        make_call est une fabrique de coroutine : chaque tentative recrée
        l'appel (et rouvre le fichier pour une photo). Après la dernière
        tentative, l'exception remonte jusqu'à l'error handler.
        """
        for attempt in range(1, SEND_ATTEMPTS + 1):
            try:
                return await make_call()
            except NetworkError as e:
                if attempt == SEND_ATTEMPTS:
                    raise
                log.warning(
                    "telegram send failed (attempt %d/%d): %s, chat_id=%s",
                    attempt, SEND_ATTEMPTS, type(e).__name__, chat_id,
                )
                await asyncio.sleep(SEND_BACKOFF_SECONDS[attempt - 1])

    async def send(self, chat_id: int, message):
        """
        Envoie la réponse du kernel, précédée de la réponse en attente.

        Si une réponse précédente n'avait pas pu partir, elle est livrée
        d'abord, après un avertissement. Si l'envoi échoue définitivement
        (réessais épuisés), la réponse courante est mémorisée pour le
        prochain envoi au lieu de remonter jusqu'à l'error handler.
        """
        pending = self.undelivered.pop(chat_id, None)
        try:
            if pending is not None:
                await self._deliver(chat_id, UNDELIVERED_NOTICE)
                await self._deliver(chat_id, pending)
            await self._deliver(chat_id, message)
            self.last_reply[chat_id] = message
        except NetworkError as e:
            log.error(
                "telegram send gave up after %d attempts: %s, chat_id=%s — réponse mise en attente",
                SEND_ATTEMPTS, type(e).__name__, chat_id,
            )
            # Une seule réponse en attente par chat : la plus récente écrase.
            self.undelivered[chat_id] = message

    async def _deliver(self, chat_id: int, message):
        """
        Envoie une réponse du kernel à l'utilisateur Telegram.

        Gère trois cas :
        - dict {"type": "image", "path": ..., "caption": ...}
            → send_photo() avec le fichier local
        - dict générique
            → extraction du champ "text" ou str()
        - str
            → send_message() direct
        - dict {"type": "images_text", "images": [...], "text": ...}
            → une send_photo() par image, puis le texte (sprint 26)
        """

        # ── Résultat texte + images (coach d'échecs) ─────────────────────────
        # Photos d'abord, puis le texte par le chemin texte ci-dessous.
        if isinstance(message, dict) and message.get("type") == "images_text":
            for image in message.get("images", []):
                path = image.get("path", "")
                caption = image.get("caption", "") or ""
                if not (path and Path(path).exists()):
                    log.warning("telegram images_text: image introuvable, ignorée: %s", path)
                    continue

                # Fichier rouvert à chaque tentative (cf. cas image ci-dessous).
                async def _send_photo(path=path, caption=caption):
                    with open(path, "rb") as photo:
                        return await self.app.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=caption[:1024] if caption else None,
                        )
                # Photo en échec définitif : sautée, la suite part quand même (#104).
                try:
                    await self._send_with_retry(chat_id, _send_photo)
                except NetworkError as e:
                    log.warning(
                        "telegram images_text: photo non envoyée, ignorée: %s (%s)",
                        path, type(e).__name__,
                    )
            message = message.get("text", "")

        # ── Résultat image ───────────────────────────────────────────────────
        if isinstance(message, dict) and message.get("type") == "image":
            path = message.get("path", "")
            caption = message.get("caption", "") or ""

            if path and Path(path).exists():
                # Fichier rouvert à chaque tentative : un handle déjà lu
                # ne peut pas être renvoyé.
                async def _send_photo():
                    with open(path, "rb") as photo:
                        return await self.app.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=caption[:1024] if caption else None,
                        )
                await self._send_with_retry(chat_id, _send_photo)
                return

            # Fichier introuvable — on envoie le path en texte (debug)
            await self._send_with_retry(chat_id, lambda: self.app.bot.send_message(
                chat_id=chat_id,
                text=f"Image générée mais fichier introuvable : {path}",
            ))
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
            await self._send_with_retry(chat_id, lambda: self.app.bot.send_message(
                chat_id=chat_id,
                text=chunk,
            ))