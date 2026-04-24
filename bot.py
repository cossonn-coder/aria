# aria/bot.py
#
# Point d'entrée du service ARIA.
#
# Responsabilité unique : instancier le kernel et démarrer l'interface Telegram.
# Aucune logique métier ici — tout est dans AriaKernel et TelegramInterface.
 
import os
from core.kernel import AriaKernel
from interfaces.telegram_interface import TelegramInterface
 
 
def main():
    kernel = AriaKernel()
    telegram = TelegramInterface(
        kernel,
        token=os.environ["ARIA_BOT_TOKEN"],
    )
    telegram.start()
 
 
if __name__ == "__main__":
    main()
 