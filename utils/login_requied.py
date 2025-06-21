from aiogram.types import Message

from db.User import User
from loguru import logger


def only_registered(func, text="Напиши /start для использования этой функции"):
    async def wrapper(message: Message):
        user = await User.aio_get_or_none(
            telegram_user_id=message.from_user.id,
            telegram_chat_id=message.chat.id,
        )
        if not user:
            logger.info(f"User {message.from_user.id} not registered")
            await message.reply(text)
            return
        return await func(message, user)

    return wrapper