def encode_nickname(nickname: str) -> str:
    """Кодирует никнейм для использования в callback_data, заменяя _ на -"""
    return nickname.replace("_", "-")


def decode_nickname(encoded_nickname: str) -> str:
    """Декодирует никнейм из callback_data, заменяя - на _"""
    return encoded_nickname.replace("-", "_") 