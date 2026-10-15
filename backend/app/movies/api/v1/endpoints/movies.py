from typing import Annotated

from fastapi import APIRouter, Query

from app.movies.api.deps import MovieServiceDep
from app.movies.schemas import MovieRead, MovieSearchItem

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/search")
async def search_movies(
    service: MovieServiceDep, q: Annotated[str, Query(min_length=2, max_length=100)]
) -> list[MovieSearchItem]:
    return [MovieSearchItem(**item.model_dump()) for item in await service.search(q)]


@router.get("/{imdb_id}")
async def get_movie(imdb_id: str, service: MovieServiceDep) -> MovieRead:
    return MovieRead.model_validate(await service.get_movie(imdb_id))
