from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.movies.models import Movie
from app.movies.schemas.imdb import ImdbMovie


class MovieRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, imdb_id: str) -> Movie | None:
        return await self._session.get(Movie, imdb_id)

    async def get_many(self, imdb_ids: Sequence[str]) -> list[Movie]:
        result = await self._session.scalars(select(Movie).where(Movie.imdb_id.in_(imdb_ids)))
        return list(result)

    async def upsert(self, data: ImdbMovie) -> Movie:
        values = data.model_dump()
        stmt = (
            insert(Movie)
            .values(**values, fetched_at=func.now())
            .on_conflict_do_update(
                index_elements=[Movie.imdb_id],
                set_={**{k: v for k, v in values.items() if k != "imdb_id"}, "fetched_at": func.now()},
            )
            .returning(Movie)
            .execution_options(populate_existing=True)
        )
        return (await self._session.execute(stmt)).scalar_one()
