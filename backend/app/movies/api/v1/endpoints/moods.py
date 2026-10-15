from fastapi import APIRouter

from app.movies.moods import MOODS
from app.movies.schemas import MoodRead

router = APIRouter(tags=["moods"])


@router.get("/moods")
async def list_moods() -> list[MoodRead]:
    return [MoodRead(key=mood.key) for mood in MOODS.values()]
