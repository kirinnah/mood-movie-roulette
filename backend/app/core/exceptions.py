class AppError(Exception):
    default_detail = "Внутренняя ошибка"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    default_detail = "Не найдено"


class ConflictError(AppError):
    default_detail = "Конфликт данных"


class UnauthorizedError(AppError):
    default_detail = "Требуется авторизация"


class UpstreamError(AppError):
    default_detail = "Внешний сервис недоступен"
