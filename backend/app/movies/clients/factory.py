from app.core.config import settings
from app.movies.clients.imdb import ImdbClient
from app.movies.clients.omdb import OmdbClient


def create_movie_client() -> ImdbClient | OmdbClient:
    if settings.movie_provider == "omdb":
        if not settings.omdb_api_key:
            raise RuntimeError("MOVIE_PROVIDER=omdb, но OMDB_API_KEY не задан")
        return OmdbClient(settings.omdb_api_key, settings.omdb_api_base, settings.imdb_timeout)
    return ImdbClient(settings.imdb_api_base, settings.imdb_timeout)
