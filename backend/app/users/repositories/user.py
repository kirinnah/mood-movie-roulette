from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.users.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        return await self._session.scalar(select(User).where(User.email == email))

    async def add(self, email: str, password_hash: str) -> User | None:
        stmt = (
            insert(User)
            .values(email=email, password_hash=password_hash)
            .on_conflict_do_nothing(index_elements=["email"])
            .returning(User)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
