# aria/bot.py
#
# Point d'entrée du service ARIA.
#
# Responsabilité unique : instancier le kernel et démarrer l'interface Telegram.
# Aucune logique métier ici — tout est dans AriaKernel et TelegramInterface.
 
import os
from logger import configure_root

configure_root(level=os.getenv("ARIA_LOG_LEVEL", "INFO"))

from core.kernel import AriaKernel
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
    telegram.start()
 
 
if __name__ == "__main__":
    main()
 