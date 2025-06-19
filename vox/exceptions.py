# src/vox_wrapper/exceptions.py

class ApiError(Exception):
    """Базовое исключение для ошибок API."""


class AuthenticationError(ApiError):
    """Ошибка авторизации (401/403)."""


class ValidationError(ApiError):
    """Ошибка валидации (422)."""

    def __init__(self, detail):
        """
        :param detail: подробности ошибки валидации (обычно JSON-объект с полем 'detail')
        """
        super().__init__("Validation failed (422)")
        self.detail = detail


class NotFoundError(ApiError):
    """Ресурс не найден (404)."""


class ServerError(ApiError):
    """Ошибка сервера (5xx)."""