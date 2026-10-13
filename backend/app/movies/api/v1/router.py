from fastapi import APIRouter

from app.movies.api.v1.endpoints import moods, movies, roulette

router = APIRouter()
router.include_router(moods.router)
router.include_router(roulette.router)
router.include_router(movies.router)
