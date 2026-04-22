#aria/bot.py
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