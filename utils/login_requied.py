from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from db.User import User
from loguru import logger
from translations.get_phrase import get_phrase


def only_registered(func, text_tag="user_not_registered"):
    async def wrapper(message: Message):
        user = await User.aio_get_or_none(
            telegram_user_id=message.from_user.id,
            telegram_chat_id=message.chat.id,
        )
        if not user:
            logger.info(f"User {message.from_user.id} not registered")
            await message.reply(get_phrase(text_tag, message.from_user.language_code))
            return
        return await func(message, user)

    return wrapper


def only_registered_callback(func, text_tag="user_not_registered"):
    async def wrapper(callback: CallbackQuery, state: FSMContext):
        user = await User.aio_get_or_none(
            telegram_user_id=callback.from_user.id,
            telegram_chat_id=callback.message.chat.id,
        )
        if not user:
            logger.info(f"User {callback.from_user.id} not registered")
            await callback.answer(
                get_phrase(text_tag, callback.from_user.language_code)
            )
            return
        return await func(callback, state, user)

    return wrapper
