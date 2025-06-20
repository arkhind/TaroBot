def get_current_username(message):
    """
    Получает никнейм пользователя Telegram из объекта message.
    :param message: объект aiogram.types.Message
    :return: str | None
    """
    username = None
    if hasattr(message, 'from_user') and message.from_user:
        username = message.from_user.username
    return username
