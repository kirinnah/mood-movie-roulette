from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.db.session import SessionDep
from app.users.models import User
from app.users.repositories.user import UserRepository
from app.users.services.user import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_user_service(session: SessionDep) -> UserService:
    return UserService(UserRepository(session))


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], service: UserServiceDep) -> User:
    return await service.get_by_token(token)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
