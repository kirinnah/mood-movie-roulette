import pytest

from app.core.exceptions import NotFoundError, UpstreamError
from app.movies.moods import MOODS
from app.movies.services.movie import MovieService
from app.movies.services.roulette import RouletteService
from tests.conftest import FakeMovieProvider, FakeMovieRepository, make_imdb_movie, make_movie

TTL_DAYS = 30
HAPPY_IDS = list(MOODS["happy"].imdb_ids)


def make_roulette(repo=None, provider=None) -> RouletteService:
    repo = repo or FakeMovieRepository()
    movies = MovieService(repo, provider or FakeMovieProvider(), TTL_DAYS)
    return RouletteService(movies, repo)


@pytest.mark.asyncio
async def test_spin_returns_movie_from_mood() -> None:
    provider = FakeMovieProvider({i: make_imdb_movie(i, f"Фильм {i}") for i in HAPPY_IDS})
    roulette = make_roulette(provider=provider)
    only = HAPPY_IDS[0]

    result = await roulette.spin("happy", exclude=set(HAPPY_IDS[1:]))

    assert result.imdb_id == only


@pytest.mark.asyncio
async def test_exclude_ids_are_not_requested() -> None:
    provider = FakeMovieProvider({i: make_imdb_movie(i, f"Фильм {i}") for i in HAPPY_IDS})
    roulette = make_roulette(provider=provider)
    excluded = set(HAPPY_IDS[1:])

    result = await roulette.spin("happy", exclude=excluded)

    assert result.imdb_id == HAPPY_IDS[0]
    assert set(provider.get_calls) == {HAPPY_IDS[0]}
    assert not (excluded & set(provider.get_calls))


@pytest.mark.asyncio
async def test_all_excluded_falls_back_to_full_mood_list() -> None:
    provider = FakeMovieProvider({i: make_imdb_movie(i, f"Фильм {i}") for i in HAPPY_IDS})
    roulette = make_roulette(provider=provider)

    result = await roulette.spin("happy", exclude=set(HAPPY_IDS))

    assert result.imdb_id in HAPPY_IDS


@pytest.mark.asyncio
async def test_unknown_mood_raises_not_found() -> None:
    roulette = make_roulette()

    with pytest.raises(NotFoundError, match="Неизвестное настроение"):
        await roulette.spin("no-such-mood", exclude=set())


@pytest.mark.asyncio
async def test_api_down_falls_back_to_cache() -> None:
    cached = [make_movie(i, f"Кэш {i}") for i in HAPPY_IDS[:2]]
    repo = FakeMovieRepository(cached)
    provider = FakeMovieProvider(error=UpstreamError("IMDb API недоступен"))
    roulette = make_roulette(repo, provider)

    result = await roulette.spin("happy", exclude=set())

    assert result.imdb_id in {m.imdb_id for m in cached}


@pytest.mark.asyncio
async def test_api_down_and_empty_cache_raises_upstream() -> None:
    provider = FakeMovieProvider(error=UpstreamError("IMDb API недоступен"))
    roulette = make_roulette(provider=provider)

    with pytest.raises(UpstreamError):
        await roulette.spin("happy", exclude=set())
