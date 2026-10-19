from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_JWT_SECRETS = {"", "change-me", "dev-secret-change-me-in-production-0123456789"}
MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Кино-рулетка по настроению"
    database_url: str = "postgresql+asyncpg://roulette:roulette@localhost:5432/roulette"
    cors_origins: list[str] = ["*"]

    movie_provider: Literal["imdbot", "omdb"] = "imdbot"
    imdb_api_base: str = "https://imdb.iamidiotareyoutoo.com"
    imdb_timeout: float = 5.0
    omdb_api_key: str = ""
    omdb_api_base: str = "https://www.omdbapi.com"
    cache_ttl_days: int = 30

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    def validate_runtime(self) -> None:
        secret = self.jwt_secret
        if secret in INSECURE_JWT_SECRETS or len(secret) < MIN_JWT_SECRET_LENGTH:
            raise RuntimeError(
            )


settings = Settings()