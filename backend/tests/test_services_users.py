import pytest

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import create_access_token, hash_password
from app.users.services.user import UserService
from tests.conftest import FakeUserRepository

PASSWORD = "password123"


def make_service(repo=None) -> UserService:
    return UserService(repo or FakeUserRepository())


@pytest.mark.asyncio
async def test_register_creates_user_with_lowercased_email() -> None:
    repo = FakeUserRepository()

    user = await make_service(repo).register("  USER@Example.COM  ".strip(), PASSWORD)

    assert user.email == "user@example.com"
    assert repo.add_calls == ["user@example.com"]
    assert user.password_hash != PASSWORD  # хранится хэш, а не пароль


@pytest.mark.asyncio
async def test_register_duplicate_raises_conflict() -> None:
    service = make_service()
    await service.register("user@example.com", PASSWORD)

    with pytest.raises(ConflictError):
        await service.register("user@example.com", "другой-пароль-1")


@pytest.mark.asyncio
async def test_authenticate_returns_user() -> None:
    service = make_service()
    await service.register("user@example.com", PASSWORD)

    user = await service.authenticate("user@example.com", PASSWORD)

    assert user.email == "user@example.com"


@pytest.mark.asyncio
async def test_authenticate_wrong_password_raises_unauthorized() -> None:
    service = make_service()
    await service.register("user@example.com", PASSWORD)

    with pytest.raises(UnauthorizedError):
        await service.authenticate("user@example.com", "wrong-password")


@pytest.mark.asyncio
async def test_authenticate_unknown_email_raises_unauthorized() -> None:
    with pytest.raises(UnauthorizedError):
        await make_service().authenticate("ghost@example.com", PASSWORD)


@pytest.mark.asyncio
async def test_token_roundtrip() -> None:
    service = make_service()
    user = await service.register("user@example.com", PASSWORD)

    token = service.issue_token(user)
    assert (await service.get_by_token(token)).id == user.id


@pytest.mark.asyncio
async def test_get_by_token_garbage_raises_unauthorized() -> None:
    with pytest.raises(UnauthorizedError):
        await make_service().get_by_token("not-a-token")


@pytest.mark.asyncio
async def test_get_by_token_unknown_user_raises_unauthorized() -> None:
    token = create_access_token("424242")

    with pytest.raises(UnauthorizedError):
        await make_service().get_by_token(token)


def test_password_longer_than_72_bytes_rejected() -> None:
    # Граница bcrypt: в HTTP-слое её ловит валидация схемы (max_length=72),
    # но сервис должен падать явно, а не молча резать пароль.
    with pytest.raises(ValueError):
        hash_password("x" * 73)
