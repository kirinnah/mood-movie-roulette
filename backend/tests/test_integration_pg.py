"""Интеграционные тесты на настоящем PostgreSQL.

Запуск: создать отдельную БД (например roulette_test) и указать DSN:
    TEST_DATABASE_URL=postgresql+asyncpg://roulette:roulette@localhost:5432/roulette_test \
        pytest -m integration

Без TEST_DATABASE_URL файл пропускается целиком.
"""

import os
import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db.base import Base
from app.core.db.session import get_session
from app.favorites.repositories.favorite import FavoriteRepository
from app.main import app
from app.movies.repositories.movie import MovieRepository
from app.users.repositories.user import UserRepository
from tests.conftest import FakeMovieProvider, make_imdb_movie

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="нужен TEST_DATABASE_URL (Postgres)"),
    pytest.mark.integration,
]

engine = create_async_engine(TEST_DATABASE_URL or "postgresql+asyncpg://", pool_pre_ping=True)
session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def _override_session() -> AsyncIterator[object]:
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(scope="module", autouse=True)
async def prepare_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session():
    async with session_factory() as s:
        yield s


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    app.state.movie_client = FakeMovieProvider()
    app.dependency_overrides[get_session] = _override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def unique_email() -> str:
    return f"it-{uuid.uuid4().hex[:12]}@example.com"


async def auth_headers(client: httpx.AsyncClient, email: str, password: str) -> dict[str, str]:
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    token = (
        await client.post("/api/v1/auth/login", data={"username": email, "password": password})
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_health_hits_real_db(client) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok"}


@pytest.mark.asyncio
async def test_movie_upsert_on_conflict_updates_row(session) -> None:
    repo = MovieRepository(session)
    await repo.upsert(make_imdb_movie("tt9999999", title="Старое название"))
    await session.commit()

    updated = await repo.upsert(make_imdb_movie("tt9999999", title="Новое название", rating=8.0))
    await session.commit()

    assert updated.title == "Новое название"
    assert updated.rating == 8.0
    stored = await repo.get("tt9999999")
    assert stored is not None and stored.title == "Новое название"


@pytest.mark.asyncio
async def test_user_add_conflict_returns_none(session) -> None:
    repo = UserRepository(session)

    created = await repo.add("dup@example.com", "hash")
    await session.commit()
    duplicate = await repo.add("dup@example.com", "другой-хэш")
    await session.commit()

    assert created is not None
    assert duplicate is None  # ON CONFLICT DO NOTHING


@pytest.mark.asyncio
async def test_favorite_add_conflict_returns_false(session) -> None:
    movies = MovieRepository(session)
    await movies.upsert(make_imdb_movie("tt9999998"))
    await session.commit()
    users = UserRepository(session)
    user = await users.add("fav@example.com", "hash")
    await session.commit()

    repo = FavoriteRepository(session)
    assert await repo.add(user.id, "tt9999998") is True
    await session.commit()
    assert await repo.add(user.id, "tt9999998") is False  # ON CONFLICT DO NOTHING


@pytest.mark.asyncio
async def test_full_auth_and_favorites_flow(client) -> None:
    email = unique_email()
    password = "password123"

    registered = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    assert registered.status_code == 201

    duplicate = await client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    assert duplicate.status_code == 409

    wrong = await client.post(
        "/api/v1/auth/login", data={"username": email, "password": "wrong-password"}
    )
    assert wrong.status_code == 401

    headers = await auth_headers(client, email, password)
    me = await client.get("/api/v1/users/me", headers=headers)
    assert me.status_code == 200 and me.json()["email"] == email

    movie_id = "tt0111161"
    added = await client.post("/api/v1/favorites", json={"imdb_id": movie_id}, headers=headers)
    assert added.status_code == 201
    assert added.json()["movie"]["imdb_id"] == movie_id

    again = await client.post("/api/v1/favorites", json={"imdb_id": movie_id}, headers=headers)
    assert again.status_code == 200

    listed = await client.get("/api/v1/favorites", headers=headers)
    assert [f["movie"]["imdb_id"] for f in listed.json()] == [movie_id]

    removed = await client.delete(f"/api/v1/favorites/{movie_id}", headers=headers)
    assert removed.status_code == 204

    empty = await client.get("/api/v1/favorites", headers=headers)
    assert empty.json() == []


@pytest.mark.asyncio
async def test_roulette_roundtrip_with_real_db(client) -> None:
    response = await client.get("/api/v1/roulette", params={"mood": "happy"})

    assert response.status_code == 200
    assert response.json()["imdb_id"].startswith("tt")

    card = await client.get(f"/api/v1/movies/{response.json()['imdb_id']}")
    assert card.status_code == 200


@pytest.mark.asyncio
async def test_favorites_hidden_from_other_user(client) -> None:
    owner = await auth_headers(client, unique_email(), "password123")
    outsider = await auth_headers(client, unique_email(), "password123")

    await client.post("/api/v1/favorites", json={"imdb_id": "tt0111161"}, headers=owner)

    assert (await client.get("/api/v1/favorites", headers=outsider)).json() == []
    await client.delete("/api/v1/favorites/tt0111161", headers=outsider)
    listed = await client.get("/api/v1/favorites", headers=owner)
    assert [f["movie"]["imdb_id"] for f in listed.json()] == ["tt0111161"]
