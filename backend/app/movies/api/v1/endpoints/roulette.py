from typing import Annotated

from fastapi import APIRouter, Query

from app.movies.api.deps import RouletteServiceDep
from app.movies.schemas.movie import MovieRead

router = APIRouter(tags=["roulette"])


@router.get("/roulette", response_model=MovieRead)
async def spin(
    service: RouletteServiceDep,
    mood: Annotated[str, Query(description="Ключ из /moods")],
    exclude: Annotated[str, Query(description="imdb_id через запятую — уже выпавшие")] = "",
):
    excluded = {x.strip() for x in exclude.split(",") if x.strip()}
    return await service.spin(mood, excluded)
