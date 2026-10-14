import logging
import random

from app.core.exceptions import AppError, UpstreamError
from app.movies.models import Movie
from app.movies.moods import get_mood
from app.movies.repositories.movie import MovieRepository
from app.movies.services.movie import MovieService

log = logging.getLogger(__name__)
MAX_ATTEMPTS = 3


class RouletteService:
    def __init__(self, movies: MovieService, repo: MovieRepository) -> None:
        self._movies = movies
        self._repo = repo

    async def spin(self, mood_key: str, exclude: set[str]) -> Movie:
        mood = get_mood(mood_key)
        candidates = [i for i in mood.imdb_ids if i not in exclude] or list(mood.imdb_ids)
        random.shuffle(candidates)

        for imdb_id in candidates[:MAX_ATTEMPTS]:
            try:
                return await self._movies.get_movie(imdb_id)
            except AppError as exc:
                log.warning("Skip %s: %s", imdb_id, exc.detail)

        cached = await self._repo.get_many(candidates)
        if cached:
            return random.choice(cached)
        raise UpstreamError("IMDb недоступен, а в кэше нет подходящих фильмов")
