from fastapi import APIRouter

from app.users.api.deps import CurrentUserDep
from app.users.schemas import UserRead

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def me(user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(user)
