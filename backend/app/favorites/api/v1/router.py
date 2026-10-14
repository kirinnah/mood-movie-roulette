from fastapi import APIRouter

from app.favorites.api.v1.endpoints import favorites

router = APIRouter()
router.include_router(favorites.router)
