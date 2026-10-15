from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.users.api.deps import UserServiceDep
from app.users.schemas import Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, service: UserServiceDep) -> UserRead:
    return UserRead.model_validate(await service.register(body.email, body.password))


@router.post("/login")
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], service: UserServiceDep) -> Token:
    """OAuth2 password flow: в поле username передаётся email."""
    user = await service.authenticate(form.username, form.password)
    return Token(access_token=service.issue_token(user))
