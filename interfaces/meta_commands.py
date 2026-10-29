# aria/interfaces/meta_commands.py
#
# Métacommandes Telegram (sprint 40, #131).
#
# Responsabilité : bâtir le texte des réponses aux commandes /xxx.
# Les handlers Telegram (minces) vivent dans TelegramInterface ; les
# commandes ne passent pas par le kernel et ne sont pas écrites dans
# l'historique de conversation.

from config import config

# Nom → description courte. Sert à /help et à set_my_commands
# (auto-complétion Telegram). Les tronçons 02-03 y ajoutent leurs commandes.
COMMANDS = {
    "help": "Liste des commandes",
    "reboot": "Redémarre ARIA",
    "board": "Lien de l'échiquier",
    "again": "Renvoie ma dernière réponse",
}

REBOOT_TEXT = "🔄 Redémarrage… (≈ 15 s)"
BACK_TEXT = "✅ De retour."
NOTHING_TO_RESEND = "Rien à renvoyer."


def help_text() -> str:
    """Une ligne par commande : « /nom — description »."""
    return "\n".join(f"/{name} — {description}" for name, description in COMMANDS.items())


def board_text() -> str:
    """URL de l'échiquier ARIA."""
    return config.board_url
