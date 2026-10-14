from typing import Annotated

from fastapi import Depends

from app.core.db.session import SessionDep
from app.favorites.repositories.favorite import FavoriteRepository
from app.favorites.services.favorite import FavoriteService
from app.movies.api.deps import MovieServiceDep


def get_favorite_service(session: SessionDep, movies: MovieServiceDep) -> FavoriteService:
    return FavoriteService(FavoriteRepository(session), movies)


FavoriteServiceDep = Annotated[FavoriteService, Depends(get_favorite_service)]
