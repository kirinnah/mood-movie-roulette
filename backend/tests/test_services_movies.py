from datetime import UTC, datetime

import pytest

from app.core.exceptions import NotFoundError, UpstreamError
from app.movies.services.movie import MovieService
from tests.conftest import (
    FakeMovieProvider,
    FakeMovieRepository,
    make_imdb_movie,
    make_movie,
    make_search_item,
)

TTL_DAYS = 30
OLD = datetime(2020, 1, 1, tzinfo=UTC)


def make_service(repo=None, provider=None):
    return MovieService(repo or FakeMovieRepository(), provider or FakeMovieProvider(), TTL_DAYS)


@pytest.mark.asyncio
async def test_fresh_cache_returns_without_api_call() -> None:
    cached = make_movie()
    repo = FakeMovieRepository([cached])
    provider = FakeMovieProvider()

    result = await make_service(repo, provider).get_movie("tt0111161")

    assert result is cached
    assert provider.get_calls == []
    assert repo.upsert_calls == []


@pytest.mark.asyncio
async def test_stale_cache_fetches_and_upserts() -> None:
    repo = FakeMovieRepository([make_movie(fetched_at=OLD)])
    provider = FakeMovieProvider({"tt0111161": make_imdb_movie(title="Новое название")})

    result = await make_service(repo, provider).get_movie("tt0111161")

    assert provider.get_calls == ["tt0111161"]
    assert repo.upsert_calls == ["tt0111161"]
    assert result.title == "Новое название"


@pytest.mark.asyncio
async def test_api_down_returns_stale_cache() -> None:
    cached = make_movie(fetched_at=OLD)
    repo = FakeMovieRepository([cached])
    provider = FakeMovieProvider(error=UpstreamError("IMDb API недоступен"))

    result = await make_service(repo, provider).get_movie("tt0111161")

    assert result is cached


@pytest.mark.asyncio
async def test_api_down_without_cache_raises_upstream() -> None:
    provider = FakeMovieProvider(error=UpstreamError("IMDb API недоступен"))

    with pytest.raises(UpstreamError):
        await make_service(FakeMovieRepository(), provider).get_movie("tt0111161")


@pytest.mark.asyncio
async def test_not_found_is_not_swallowed_by_cache_logic() -> None:
    repo = FakeMovieRepository([make_movie(fetched_at=OLD)])
    provider = FakeMovieProvider(movies={})

    with pytest.raises(NotFoundError):
        await make_service(repo, provider).get_movie("tt0111161")


@pytest.mark.asyncio
async def test_search_delegates_to_provider() -> None:
    provider = FakeMovieProvider(search_results=[make_search_item()])

    result = await make_service(provider=provider).search("shawshank")

    assert provider.search_calls == ["shawshank"]
    assert [i.imdb_id for i in result] == ["tt0111161"]
