from app.core.exceptions import NotFoundError
from app.favorites.models import Favorite
from app.favorites.repositories.favorite import FavoriteRepository
from app.movies.services.movie import MovieService


class FavoriteService:
    def __init__(self, repo: FavoriteRepository, movies: MovieService) -> None:
        self._repo = repo
        self._movies = movies

    async def list(self, user_id: int) -> list[Favorite]:
        return await self._repo.list_by_user(user_id)

    async def add(self, user_id: int, imdb_id: str) -> tuple[Favorite, bool]:
        await self._movies.get_movie(imdb_id)  
        created = await self._repo.add(user_id, imdb_id)
        favorite = await self._repo.get(user_id, imdb_id)
        if favorite is None: 
            raise NotFoundError("Не удалось добавить в избранное")
        return favorite, created

    async def remove(self, user_id: int, imdb_id: str) -> None:
        await self._repo.remove(user_id, imdb_id)
