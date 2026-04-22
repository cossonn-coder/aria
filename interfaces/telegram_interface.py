#aria/interfaces/telegram_interface.py
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)
from collections import defaultdict
import asyncio
from interfaces.base_interface import BaseInterface


class TelegramInterface(BaseInterface):

    def __init__(self, kernel, token: str):
        super().__init__(kernel)
        self.token = token
        self.user_locks = defaultdict(asyncio.Lock)

    def start(self):

        self.app = ApplicationBuilder().token(self.token).build()

        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        self.app.run_polling()

    async def _handle_message(self, update: Update, context):

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        text = update.message.text

        async with self.user_locks[user_id]:

            response = await self.kernel.handle_message(
                message=text,
                metadata={"user_id": user_id},
            )

        await self.send(chat_id, response)

    async def send(self, chat_id: int, message: str):
        await self.app.bot.send_message(chat_id=chat_id, text=message)