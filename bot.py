# aria/bot.py
#
# Point d'entrée du service ARIA.
#
# Responsabilité unique : instancier le kernel et démarrer l'interface Telegram.
# Aucune logique métier ici — tout est dans AriaKernel et TelegramInterface.
 
import logging
import os
from logger import configure_root

configure_root(level=os.getenv("ARIA_LOG_LEVEL", "INFO"))

from core.kernel import AriaKernel
from interfaces.board_interface import start_board_server
from interfaces.telegram_interface import TelegramInterface
 
 
def main():
    from logger import get_logger
    log = get_logger(__name__)
    log.info("ARIA démarrage")

    kernel = AriaKernel()
    telegram = TelegramInterface(
        kernel,
        token=os.environ["ARIA_BOT_TOKEN"],
    )
    log.info("Telegram interface prête")
    # Échiquier ARIA (sprint 35) : threads daemon, tués par os._exit à l'arrêt.
    start_board_server()
    telegram.start()

    # Sortie immédiate, sans finalisation Python : sous swap, le ramasse-miettes
    # et les destructeurs de fin de processus prenaient de 9 s à plus de 90 s
    # (relecture des pages swappées) et systemd finissait par SIGKILL.
    # Rien n'est perdu : PTB est déjà arrêté proprement et le sqlite de
    # chromadb est validé à chaque écriture. On vide seulement les logs.
    log.info("ARIA arrêt")
    logging.shutdown()
    os._exit(0)
 
 
if __name__ == "__main__":
    main()
 