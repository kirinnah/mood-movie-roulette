import httpx
import pytest

from app.core.exceptions import NotFoundError, UpstreamError
from app.movies.clients.omdb import OmdbClient

API_KEY = "test-key"

OMDB_PAYLOAD = {
    "Title": "The Shawshank Redemption",
    "Year": "1994",
    "imdbRating": "9.3",
    "Poster": "https://example.com/poster.jpg",
    "Plot": "Краткий сюжет",
    "Genre": "Drama, Crime",
    "Actors": "Tim Robbins, Morgan Freeman",
    "Response": "True",
}


def make_client(handler, **kwargs) -> OmdbClient:
    transport = httpx.MockTransport(handler)
    kwargs.setdefault("retries", 3)
    kwargs.setdefault("backoff", 0)
    return OmdbClient(API_KEY, transport=transport, **kwargs)


@pytest.mark.asyncio
async def test_get_movie_maps_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["i"] == "tt0111161"
        assert request.url.params["apikey"] == API_KEY
        return httpx.Response(200, json=OMDB_PAYLOAD)

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
async def test_na_values_become_none() -> None:
    payload = {**OMDB_PAYLOAD, "Year": "N/A", "imdbRating": "N/A",
               "Poster": "N/A", "Plot": "N/A", "Genre": "N/A", "Actors": "N/A"}

    movie = await make_client(lambda req: httpx.Response(200, json=payload)).get_movie("tt0111161")

    assert movie.year is None
    assert movie.rating is None
    assert movie.poster_url is None
    assert movie.description is None
    assert movie.genres == []
    assert movie.actors == []


@pytest.mark.asyncio
async def test_movie_not_found_raises_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Response": "False", "Error": "Movie not found!"})

    with pytest.raises(NotFoundError):
        await make_client(handler).get_movie("tt0000000")


@pytest.mark.asyncio
async def test_invalid_api_key_raises_upstream_without_retry() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(200, json={"Response": "False", "Error": "Invalid API key!"})

    with pytest.raises(UpstreamError):
        await make_client(handler).get_movie("tt0111161")

    assert attempts == 1


@pytest.mark.asyncio
async def test_retries_on_500_then_success() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(500)
        return httpx.Response(200, json=OMDB_PAYLOAD)

    movie = await make_client(handler).get_movie("tt0111161")

    assert attempts == 3
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
async def test_search_maps_items_and_filters_non_imdb_ids() -> None:
    payload = {
        "Response": "True",
        "Search": [
            {"imdbID": "tt0111161", "Title": "Shawshank", "Year": "1994", "Poster": "N/A"},
            {"imdbID": "nm0000134", "Title": "Не фильм", "Year": "1990", "Poster": "x"},
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["s"] == "shawshank"
        assert request.url.params["type"] == "movie"
        return httpx.Response(200, json=payload)

    items = await make_client(handler).search("shawshank")

    assert [i.imdb_id for i in items] == ["tt0111161"]
    assert items[0].title == "Shawshank"
    assert items[0].year == 1994
    assert items[0].poster_url is None


@pytest.mark.asyncio
async def test_search_not_found_returns_empty_list() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Response": "False", "Error": "Movie not found!"})

    assert await make_client(handler).search("zzzz-nothing") == []


@pytest.mark.asyncio
async def test_get_movie_without_title_raises_not_found() -> None:
    payload = {**OMDB_PAYLOAD, "Title": "N/A"}
    with pytest.raises(NotFoundError):
        await make_client(lambda req: httpx.Response(200, json=payload)).get_movie("tt0111161")
