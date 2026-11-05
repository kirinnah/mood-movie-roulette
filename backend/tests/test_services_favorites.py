import pytest

from app.core.exceptions import NotFoundError
from app.favorites.services.favorite import FavoriteService
from app.movies.services.movie import MovieService
from tests.conftest import FakeFavoriteRepository, FakeMovieProvider, FakeMovieRepository

TTL_DAYS = 30


def make_service(fav_repo=None, movie_repo=None, provider=None) -> FavoriteService:
    movies = MovieService(movie_repo or FakeMovieRepository(), provider or FakeMovieProvider(), TTL_DAYS)
    return FavoriteService(fav_repo or FakeFavoriteRepository(), movies)


@pytest.mark.asyncio
async def test_add_new_favorite_returns_created_true() -> None:
    service = make_service()

    favorite, created = await service.add(1, "tt0111161")

    assert created is True
    assert favorite.imdb_id == "tt0111161"


@pytest.mark.asyncio
async def test_add_duplicate_is_not_an_error() -> None:
    service = make_service()

    _, created_first = await service.add(1, "tt0111161")
    favorite, created_second = await service.add(1, "tt0111161")

    assert created_first is True
    assert created_second is False
    assert favorite.imdb_id == "tt0111161"


@pytest.mark.asyncio
async def test_add_fetches_movie_from_provider_first() -> None:
    provider = FakeMovieProvider()
    service = make_service(provider=provider)

    await service.add(1, "tt0111161")

    assert provider.get_calls == ["tt0111161"]


@pytest.mark.asyncio
async def test_add_unknown_movie_raises_not_found() -> None:
    provider = FakeMovieProvider(movies={})
    service = make_service(provider=provider)

    with pytest.raises(NotFoundError):
        await service.add(1, "tt0000000")


@pytest.mark.asyncio
async def test_list_returns_only_user_favorites() -> None:
    service = make_service()
    await service.add(1, "tt0111161")
    await service.add(2, "tt0111161")

    favorites = await service.list(1)

    assert [f.user_id for f in favorites] == [1]


@pytest.mark.asyncio
async def test_remove_deletes_favorite() -> None:
    service = make_service()
    await service.add(1, "tt0111161")

    await service.remove(1, "tt0111161")

    assert await service.list(1) == []
