from fastapi import APIRouter

from app.movies.moods import MOODS
from app.movies.schemas.movie import MoodRead

router = APIRouter(tags=["moods"])


@router.get("/moods", response_model=list[MoodRead])
async def list_moods():
    return list(MOODS.values())
