import httpx
import pytest

from app.core.exceptions import NotFoundError, UpstreamError
from app.movies.clients.imdb import ImdbClient

IMDB_PAYLOAD = {
    "short": {
        "name": "The Shawshank Redemption",
        "datePublished": "1994-09-23",
        "aggregateRating": {"ratingValue": 9.3},
        "image": "https://example.com/poster.jpg",
        "description": "Краткий сюжет",
        "genre": ["Drama", "Crime"],
        "actor": [{"name": "Tim Robbins"}, {"name": "Morgan Freeman"}, {}],
    }
}


def make_client(handler, **kwargs) -> ImdbClient:
    transport = httpx.MockTransport(handler)
    kwargs.setdefault("retries", 3)
    kwargs.setdefault("backoff", 0)
    return ImdbClient("https://imdb.test", transport=transport, **kwargs)


@pytest.mark.asyncio
async def test_get_movie_maps_nested_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["tt"] == "tt0111161"
        return httpx.Response(200, json=IMDB_PAYLOAD)

    movie = await make_client(handler).get_movie("tt0111161")

    assert movie.imdb_id == "tt0111161"
    assert movie.title == "The Shawshank Redemption"
    assert movie.year == 1994
    assert movie.rating == 9.3
    assert movie.poster_url == "https://example.com/poster.jpg"
    assert movie.description == "Краткий сюжет"
    assert movie.genres == ["Drama", "Crime"]
    assert movie.actors == ["Tim Robbins", "Morgan Freeman"]


@pytest.mark.asyncio
async def test_genre_as_plain_string_becomes_single_item_list() -> None:
    payload = {"short": {**IMDB_PAYLOAD["short"], "genre": "Drama"}}

    movie = await make_client(lambda req: httpx.Response(200, json=payload)).get_movie("tt0111161")

    assert movie.genres == ["Drama"]


@pytest.mark.asyncio
async def test_missing_rating_and_image_become_none() -> None:
    short = {k: v for k, v in IMDB_PAYLOAD["short"].items()
             if k not in ("aggregateRating", "image")}
    payload = {"short": short}

    movie = await make_client(lambda req: httpx.Response(200, json=payload)).get_movie("tt0111161")

    assert movie.rating is None
    assert movie.poster_url is None


@pytest.mark.asyncio
async def test_movie_without_name_raises_not_found() -> None:
    with pytest.raises(NotFoundError):
        await make_client(lambda req: httpx.Response(200, json={"short": {}})).get_movie("tt0000000")


@pytest.mark.asyncio
async def test_retries_on_500_then_success() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(500)
        return httpx.Response(200, json=IMDB_PAYLOAD)

    movie = await make_client(handler).get_movie("tt0111161")

    assert attempts == 2
    assert movie.title == "The Shawshank Redemption"


@pytest.mark.asyncio
async def test_all_retries_exhausted_raises_upstream() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(503)

    with pytest.raises(UpstreamError):
        await make_client(handler).get_movie("tt0111161")

    assert attempts == 3


@pytest.mark.asyncio
async def test_search_maps_items() -> None:
    payload = {
        "description": [
            {"#IMDB_ID": "tt0111161", "#TITLE": "Shawshank", "#YEAR": "1994",
             "#ACTORS": "Tim Robbins", "#IMG_POSTER": "https://example.com/p.jpg"},
            {"#IMDB_ID": "tt9999999"},
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["q"] == "shawshank"
        return httpx.Response(200, json=payload)

    items = await make_client(handler).search("shawshank")

    assert len(items) == 2
    assert items[0].imdb_id == "tt0111161"
    assert items[0].title == "Shawshank"
    assert items[0].year == 1994
    assert items[0].actors == "Tim Robbins"
    assert items[1].title is None
