from typing import Annotated

from fastapi import Depends, Request

from app.core.config import settings
from app.core.db.session import SessionDep
from app.movies.repositories.movie import MovieRepository
from app.movies.services.movie import MovieProvider, MovieService
from app.movies.services.roulette import RouletteService


def get_movie_client(request: Request) -> MovieProvider:
    return request.app.state.movie_client


MovieClientDep = Annotated[MovieProvider, Depends(get_movie_client)]


def get_movie_service(session: SessionDep, client: MovieClientDep) -> MovieService:
    return MovieService(MovieRepository(session), client, settings.cache_ttl_days)


MovieServiceDep = Annotated[MovieService, Depends(get_movie_service)]


def get_roulette_service(session: SessionDep, movies: MovieServiceDep) -> RouletteService:
    return RouletteService(movies, MovieRepository(session))


RouletteServiceDep = Annotated[RouletteService, Depends(get_roulette_service)]
