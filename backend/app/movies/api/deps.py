from typing import Annotated

from fastapi import Depends, Request

from app.core.config import settings
from app.core.db.session import SessionDep
from app.movies.clients.imdb import ImdbClient
from app.movies.repositories.movie import MovieRepository
from app.movies.services.movie import MovieService
from app.movies.services.roulette import RouletteService


def get_imdb_client(request: Request) -> ImdbClient:
    return request.app.state.imdb_client


ImdbClientDep = Annotated[ImdbClient, Depends(get_imdb_client)]


def get_movie_service(session: SessionDep, imdb: ImdbClientDep) -> MovieService:
    return MovieService(MovieRepository(session), imdb, settings.cache_ttl_days)


MovieServiceDep = Annotated[MovieService, Depends(get_movie_service)]


def get_roulette_service(session: SessionDep, movies: MovieServiceDep) -> RouletteService:
    return RouletteService(movies, MovieRepository(session))


RouletteServiceDep = Annotated[RouletteService, Depends(get_roulette_service)]
