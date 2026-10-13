from fastapi import APIRouter

from app.users.api.deps import CurrentUserDep
from app.users.schemas.user import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUserDep):
    return user
