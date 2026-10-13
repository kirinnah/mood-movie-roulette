from fastapi import APIRouter

from app.users.api.v1.endpoints import auth, users

router = APIRouter()
router.include_router(auth.router)
router.include_router(users.router)
