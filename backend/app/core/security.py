from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    minutes = settings.access_token_expire_minutes if expires_minutes is None else expires_minutes
    payload = {"sub": subject, "exp": datetime.now(UTC) + timedelta(minutes=minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Возвращает subject или бросает UnauthorizedError."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Невалидный или просроченный токен") from exc
    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError("Невалидный токен")
    return str(subject)
