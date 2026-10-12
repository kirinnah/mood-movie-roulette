from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Кино-рулетка по настроению"
    database_url: str = "postgresql+asyncpg://roulette:roulette@localhost:5432/roulette"
    cors_origins: list[str] = ["*"]

    imdb_api_base: str = "https://imdb.iamidiotareyoutoo.com"
    imdb_timeout: float = 10.0
    cache_ttl_days: int = 30

    jwt_secret: str = "dev-secret-change-me-in-production-0123456789"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60


settings = Settings()
