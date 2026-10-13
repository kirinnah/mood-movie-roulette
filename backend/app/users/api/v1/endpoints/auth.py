from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.users.api.deps import UserServiceDep
from app.users.schemas.user import Token, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, service: UserServiceDep):
    return await service.register(body.email, body.password)


@router.post("/login", response_model=Token)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], service: UserServiceDep):
    user = await service.authenticate(form.username, form.password)
    return Token(access_token=service.issue_token(user))
