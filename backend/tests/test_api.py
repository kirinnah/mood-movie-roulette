"""HTTP-тесты приложения через httpx.ASGITransport с фейковыми зависимостями."""

from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.exc import OperationalError

from app.core.db.session import get_session
from app.core.security import create_access_token
from app.favorites.api.deps import get_favorite_service
from app.favorites.services.favorite import FavoriteService
from app.main import app
from app.movies.api.deps import get_movie_service, get_roulette_service
from app.movies.moods import MOODS
from app.movies.services.movie import MovieService
from app.movies.services.roulette import RouletteService
from app.users.api.deps import get_user_service
from app.users.services.user import UserService
from tests.conftest import (
    FakeFavoriteRepository,
    FakeMovieProvider,
    FakeMovieRepository,
    FakeUserRepository,
    make_imdb_movie,
    make_search_item,
)

PASSWORD = "password123"
HAPPY_IDS = list(MOODS["happy"].imdb_ids)

API = "http://test/api/v1"


class _SessionOk:
    async def execute(self, stmt):
        return None


class _SessionDown:
    async def execute(self, stmt):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def override_session(session_obj):
    async def _override() -> AsyncIterator[object]:
        yield session_obj

    app.dependency_overrides[get_session] = _override


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app.state.movie_client = FakeMovieProvider()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def user_service() -> UserService:
    service = UserService(FakeUserRepository())
    app.dependency_overrides[get_user_service] = lambda: service
    return service


@pytest.fixture
def favorite_service() -> FavoriteService:
    movies = MovieService(FakeMovieRepository(), FakeMovieProvider(), 30)
    service = FavoriteService(FakeFavoriteRepository(), movies)
    app.dependency_overrides[get_favorite_service] = lambda: service
    return service


def override_roulette(provider: FakeMovieProvider | None = None) -> None:
    repo = FakeMovieRepository()
    movies = MovieService(repo, provider or FakeMovieProvider(), 30)
    app.dependency_overrides[get_roulette_service] = lambda: RouletteService(movies, repo)


def override_movies(provider: FakeMovieProvider) -> None:
    app.dependency_overrides[get_movie_service] = lambda: MovieService(
        FakeMovieRepository(), provider, 30
    )


async def register(client: httpx.AsyncClient, email: str, password: str = PASSWORD) -> httpx.Response:
    return await client.post(f"{API}/auth/register", json={"email": email, "password": password})


@pytest.mark.asyncio
async def test_health_ok(client) -> None:
    override_session(_SessionOk())

    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


@pytest.mark.asyncio
async def test_health_db_down_returns_503(client) -> None:
    override_session(_SessionDown())

    response = await client.get("/health")

    assert response.status_code == 503
    assert "detail" in response.json()


@pytest.mark.asyncio
async def test_moods_lists_seven_keys(client) -> None:
    response = await client.get(f"{API}/moods")

    assert response.status_code == 200
    keys = [m["key"] for m in response.json()]
    assert keys == ["happy", "sad", "cozy", "adventure", "scary", "thoughtful", "romantic"]


@pytest.mark.asyncio
async def test_roulette_returns_movie(client) -> None:
    provider = FakeMovieProvider({i: make_imdb_movie(i, f"Фильм {i}") for i in HAPPY_IDS})
    override_roulette(provider)

    response = await client.get(
        f"{API}/roulette", params={"mood": "happy", "exclude": ",".join(HAPPY_IDS[1:])}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["imdb_id"] == HAPPY_IDS[0]
    assert body["title"]


@pytest.mark.asyncio
async def test_roulette_unknown_mood_returns_404(client) -> None:
    override_roulette()

    response = await client.get(f"{API}/roulette", params={"mood": "no-such-mood"})

    assert response.status_code == 404
    assert "Неизвестное настроение" in response.json()["detail"]


@pytest.mark.asyncio
async def test_movie_card_returns_fields(client) -> None:
    override_movies(FakeMovieProvider())

    response = await client.get(f"{API}/movies/tt0111161")

    assert response.status_code == 200
    body = response.json()
    assert body["imdb_id"] == "tt0111161"
    assert body["title"] == "Побег из Шоушенка"
    assert body["year"] == 1994
    assert body["genres"] == ["Drama"]
    assert "fetched_at" not in body


@pytest.mark.asyncio
async def test_search_returns_items(client) -> None:
    provider = FakeMovieProvider(search_results=[make_search_item()])
    override_movies(provider)

    response = await client.get(f"{API}/movies/search", params={"q": "shawshank"})

    assert response.status_code == 200
    assert response.json()[0]["imdb_id"] == "tt0111161"
    assert provider.search_calls == ["shawshank"]


@pytest.mark.asyncio
async def test_search_query_shorter_than_two_chars_returns_422(client) -> None:
    response = await client.get(f"{API}/movies/search", params={"q": "a"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_returns_201(client, user_service) -> None:
    response = await register(client, "user@example.com")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["id"] == 1
    assert "created_at" in body


@pytest.mark.asyncio
async def test_register_uppercase_email_is_normalized(client, user_service) -> None:
    response = await register(client, "USER@EXAMPLE.COM")

    assert response.status_code == 201
    assert response.json()["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_returns_409(client, user_service) -> None:
    await register(client, "user@example.com")

    response = await register(client, "user@example.com")

    assert response.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("password", ["short7", "x" * 73])
async def test_register_password_out_of_bounds_returns_422(client, user_service, password) -> None:
    response = await register(client, "user@example.com", password)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email_returns_422(client, user_service) -> None:
    response = await register(client, "not-an-email")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_returns_token(client, user_service) -> None:
    await register(client, "user@example.com")

    response = await client.post(
        f"{API}/auth/login", data={"username": "user@example.com", "password": PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client, user_service) -> None:
    await register(client, "user@example.com")

    response = await client.post(
        f"{API}/auth/login", data={"username": "user@example.com", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_login_accepts_form_not_json(client, user_service) -> None:
    await register(client, "user@example.com")

    response = await client.post(
        f"{API}/auth/login",
        json={"username": "user@example.com", "password": PASSWORD},
    )

    assert response.status_code in (401, 422)  # JSON не принимается, ждём form-urlencoded


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client) -> None:
    response = await client.get(f"{API}/users/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_expired_token_returns_401(client, user_service) -> None:
    user = await user_service.register("user@example.com", PASSWORD)
    expired = create_access_token(str(user.id), expires_minutes=-1)

    response = await client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_valid_token_returns_user(client, user_service) -> None:
    user = await user_service.register("user@example.com", PASSWORD)
    token = user_service.issue_token(user)

    response = await client.get(f"{API}/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_favorites_require_auth(client, favorite_service) -> None:
    response = await client.get(f"{API}/favorites")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_favorites_add_list_and_remove(client, user_service, favorite_service) -> None:
    user = await user_service.register("user@example.com", PASSWORD)
    token = user_service.issue_token(user)
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post(f"{API}/favorites", json={"imdb_id": "tt0111161"}, headers=headers)
    assert created.status_code == 201
    assert created.json()["movie"]["imdb_id"] == "tt0111161"

    duplicate = await client.post(f"{API}/favorites", json={"imdb_id": "tt0111161"}, headers=headers)
    assert duplicate.status_code == 200  # идемпотентный повтор — не ошибка

    listed = await client.get(f"{API}/favorites", headers=headers)
    assert listed.status_code == 200
    assert [f["movie"]["imdb_id"] for f in listed.json()] == ["tt0111161"]

    removed = await client.delete(f"{API}/favorites/tt0111161", headers=headers)
    assert removed.status_code == 204

    assert (await client.get(f"{API}/favorites", headers=headers)).json() == []


@pytest.mark.asyncio
async def test_favorites_invalid_imdb_id_returns_422(client, user_service, favorite_service) -> None:
    user = await user_service.register("user@example.com", PASSWORD)
    headers = {"Authorization": f"Bearer {user_service.issue_token(user)}"}

    response = await client.post(f"{API}/favorites", json={"imdb_id": "tt1"}, headers=headers)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_favorites_are_per_user(client, user_service, favorite_service) -> None:
    first = await user_service.register("first@example.com", PASSWORD)
    second = await user_service.register("second@example.com", PASSWORD)
    await client.post(
        f"{API}/favorites",
        json={"imdb_id": "tt0111161"},
        headers={"Authorization": f"Bearer {user_service.issue_token(first)}"},
    )

    response = await client.get(
        f"{API}/favorites", headers={"Authorization": f"Bearer {user_service.issue_token(second)}"}
    )

    assert response.json() == []
