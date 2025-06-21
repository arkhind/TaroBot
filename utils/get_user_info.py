from aiogram.types import Message, CallbackQuery


def get_current_username(message: Message | CallbackQuery) -> str | None:
    if isinstance(message, (Message, CallbackQuery)) and message.from_user:
        return message.from_user.username
    return None


def get_language(message: Message | CallbackQuery | CallbackQuery) -> str | None:
    if isinstance(message, (Message, CallbackQuery)) and message.from_user:
        return message.from_user.language
    return None
