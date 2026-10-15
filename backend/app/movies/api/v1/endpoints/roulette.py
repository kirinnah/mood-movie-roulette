from typing import Annotated

from fastapi import APIRouter, Query

from app.movies.api.deps import RouletteServiceDep
from app.movies.schemas import MovieRead

router = APIRouter(tags=["roulette"])


@router.get("/roulette")
async def spin(
    service: RouletteServiceDep,
    mood: Annotated[str, Query(description="Ключ из /moods")],
    exclude: Annotated[str, Query(description="imdb_id через запятую — уже выпавшие")] = "",
) -> MovieRead:
    excluded = {x.strip() for x in exclude.split(",") if x.strip()}
    return MovieRead.model_validate(await service.spin(mood, excluded))
