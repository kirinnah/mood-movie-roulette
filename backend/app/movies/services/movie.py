from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.core.exceptions import UpstreamError
from app.movies.models import Movie
from app.movies.repositories.movie import MovieRepository
from app.movies.schemas.imdb import ImdbMovie, ImdbSearchItem


class MovieProvider(Protocol):
    async def get_movie(self, imdb_id: str) -> ImdbMovie: ...
    async def search(self, query: str) -> list[ImdbSearchItem]: ...


class MovieService:
    def __init__(self, repo: MovieRepository, provider: MovieProvider, cache_ttl_days: int) -> None:
        self._repo = repo
        self._provider = provider
        self._ttl = timedelta(days=cache_ttl_days)

    async def get_movie(self, imdb_id: str) -> Movie:
        cached = await self._repo.get(imdb_id)
        if cached and datetime.now(UTC) - cached.fetched_at < self._ttl:
            return cached
        try:
            fresh = await self._provider.get_movie(imdb_id)
        except UpstreamError:
            if cached: 
                return cached
            raise
        return await self._repo.upsert(fresh)

    async def search(self, query: str) -> list[ImdbSearchItem]:
        return await self._provider.search(query)
