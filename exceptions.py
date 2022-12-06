class NotForSending(Exception):
    """Не для пересылки в телеграм."""
    pass


class TelegramMessageSendError(NotForSending):
    """Ошибка телеграма."""
    pass


class ConnectionError(Exception):
    """Не верный код ответа."""
    pass