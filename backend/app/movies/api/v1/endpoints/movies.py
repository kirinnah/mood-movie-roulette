from typing import Annotated

from fastapi import APIRouter, Query

from app.movies.api.deps import MovieServiceDep
from app.movies.schemas.movie import MovieRead, MovieSearchItem

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/search", response_model=list[MovieSearchItem])
async def search_movies(service: MovieServiceDep, q: Annotated[str, Query(min_length=2, max_length=100)]):
    return await service.search(q)


@router.get("/{imdb_id}", response_model=MovieRead)
async def get_movie(imdb_id: str, service: MovieServiceDep):
    return await service.get_movie(imdb_id)
