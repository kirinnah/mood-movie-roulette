import pytest

from app.core.config import INSECURE_JWT_SECRETS, MIN_JWT_SECRET_LENGTH, Settings


def test_valid_secret_passes() -> None:
    Settings(jwt_secret="s" * MIN_JWT_SECRET_LENGTH).validate_runtime()


@pytest.mark.parametrize("secret", ["", "short-secret", "change-me"])
def test_empty_or_short_secret_fails(secret: str) -> None:
    with pytest.raises(RuntimeError):
        Settings(jwt_secret=secret).validate_runtime()


@pytest.mark.parametrize("secret", INSECURE_JWT_SECRETS)
def test_known_insecure_defaults_fail(secret: str) -> None:
    with pytest.raises(RuntimeError):
        Settings(jwt_secret=secret).validate_runtime()
