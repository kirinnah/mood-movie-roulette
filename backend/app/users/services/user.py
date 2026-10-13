import asyncio

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.users.models import User
from app.users.repositories.user import UserRepository


class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self._repo = repo

    async def register(self, email: str, password: str) -> User:
        password_hash = await asyncio.to_thread(hash_password, password)  # bcrypt блокирующий
        user = await self._repo.add(email.lower(), password_hash)
        if user is None:
            raise ConflictError("Пользователь с таким email уже существует")
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self._repo.get_by_email(email.lower())
        if user is None or not await asyncio.to_thread(verify_password, password, user.password_hash):
            raise UnauthorizedError("Неверный email или пароль")
        return user

    def issue_token(self, user: User) -> str:
        return create_access_token(str(user.id))

    async def get_by_token(self, token: str) -> User:
        subject = decode_access_token(token)
        try:
            user_id = int(subject)
        except ValueError:
            raise UnauthorizedError("Невалидный токен") from None
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UnauthorizedError("Пользователь не найден")
        return user
