from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.favorites.models import Favorite


class FavoriteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_by_user(self, user_id: int) -> list[Favorite]:
        stmt = (
            select(Favorite)
            .options(joinedload(Favorite.movie))
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.created_at.desc(), Favorite.id.desc())
        )
        return list((await self._session.scalars(stmt)).all())

    async def get(self, user_id: int, imdb_id: str) -> Favorite | None:
        stmt = (
            select(Favorite)
            .options(joinedload(Favorite.movie))
            .where(Favorite.user_id == user_id, Favorite.imdb_id == imdb_id)
        )
        return await self._session.scalar(stmt)

    async def add(self, user_id: int, imdb_id: str) -> bool:
        stmt = (
            insert(Favorite)
            .values(user_id=user_id, imdb_id=imdb_id)
            .on_conflict_do_nothing(index_elements=["user_id", "imdb_id"])
            .returning(Favorite.id)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none() is not None

    async def remove(self, user_id: int, imdb_id: str) -> None:
        await self._session.execute(
            delete(Favorite).where(Favorite.user_id == user_id, Favorite.imdb_id == imdb_id)
        )
