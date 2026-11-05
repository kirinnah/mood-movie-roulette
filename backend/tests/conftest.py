import os
from datetime import UTC, datetime

os.environ.setdefault("MOVIE_PROVIDER", "imdbot")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-" + "x" * 48)
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://roulette:roulette@localhost:5432/roulette"
)

import pytest  # noqa: E402

from app.core.exceptions import NotFoundError  # noqa: E402
from app.favorites.models import Favorite  # noqa: E402
from app.movies.models import Movie  # noqa: E402
from app.movies.schemas.imdb import ImdbMovie, ImdbSearchItem  # noqa: E402
from app.users.models import User  # noqa: E402


def make_movie(imdb_id: str = "tt0111161", title: str = "Побег из Шоушенка", **overrides) -> Movie:
    values = {
        "imdb_id": imdb_id,
        "title": title,
        "year": 1994,
        "rating": 9.3,
        "poster_url": "https://example.com/poster.jpg",
        "description": "Описание фильма",
        "genres": ["Drama"],
        "actors": ["Тим Роббинс"],
        "fetched_at": datetime.now(UTC),
    }
    values.update(overrides)
    return Movie(**values)


def make_imdb_movie(imdb_id: str = "tt0111161", title: str = "Побег из Шоушенка", **overrides) -> ImdbMovie:
    values = {
        "imdb_id": imdb_id,
        "title": title,
        "year": 1994,
        "rating": 9.3,
        "poster_url": "https://example.com/poster.jpg",
        "description": "Описание фильма",
        "genres": ["Drama"],
        "actors": ["Тим Роббинс"],
    }
    values.update(overrides)
    return ImdbMovie(**values)


def make_search_item(imdb_id: str = "tt0111161", title: str = "Побег из Шоушенка") -> ImdbSearchItem:
    return ImdbSearchItem(imdb_id=imdb_id, title=title, year=1994, actors=None,
                          poster_url="https://example.com/poster.jpg")


def make_user(user_id: int = 1, email: str = "user@example.com") -> User:
    return User(id=user_id, email=email, password_hash="hash", created_at=datetime.now(UTC))


def make_favorite(user_id: int = 1, imdb_id: str = "tt0111161", movie: Movie | None = None) -> Favorite:
    return Favorite(
        id=1,
        user_id=user_id,
        imdb_id=imdb_id,
        created_at=datetime.now(UTC),
        movie=movie or make_movie(imdb_id),
    )


class FakeMovieProvider:
    def __init__(self, movies: dict[str, ImdbMovie] | None = None,
                 error: Exception | None = None,
                 search_results: list[ImdbSearchItem] | None = None) -> None:
        self._movies = movies if movies is not None else {"tt0111161": make_imdb_movie()}
        self._error = error
        self._search_results = search_results or []
        self.get_calls: list[str] = []
        self.search_calls: list[str] = []

    async def get_movie(self, imdb_id: str) -> ImdbMovie:
        self.get_calls.append(imdb_id)
        if self._error is not None:
            raise self._error
        try:
            return self._movies[imdb_id]
        except KeyError:
            raise NotFoundError("Фильм не найден") from None

    async def search(self, query: str) -> list[ImdbSearchItem]:
        self.search_calls.append(query)
        if self._error is not None:
            raise self._error
        return self._search_results


class FakeMovieRepository:
    def __init__(self, movies: list[Movie] | None = None) -> None:
        self.storage: dict[str, Movie] = {m.imdb_id: m for m in movies or []}
        self.upsert_calls: list[str] = []

    async def get(self, imdb_id: str) -> Movie | None:
        return self.storage.get(imdb_id)

    async def get_many(self, imdb_ids) -> list[Movie]:
        return [self.storage[i] for i in imdb_ids if i in self.storage]

    async def upsert(self, data: ImdbMovie) -> Movie:
        self.upsert_calls.append(data.imdb_id)
        movie = make_movie(
            imdb_id=data.imdb_id,
            title=data.title,
            year=data.year,
            rating=data.rating,
            poster_url=data.poster_url,
            description=data.description,
            genres=data.genres,
            actors=data.actors,
        )
        self.storage[data.imdb_id] = movie
        return movie


class FakeUserRepository:
    def __init__(self) -> None:
        self.users: dict[int, User] = {}
        self.next_id = 1
        self.add_calls: list[str] = []

    async def get_by_id(self, user_id: int) -> User | None:
        return self.users.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self.users.values() if u.email == email), None)

    async def add(self, email: str, password_hash: str) -> User | None:
        self.add_calls.append(email)
        if await self.get_by_email(email) is not None:
            return None
        user = make_user(user_id=self.next_id, email=email)
        user.password_hash = password_hash
        self.users[user.id] = user
        self.next_id += 1
        return user


class FakeFavoriteRepository:
    def __init__(self, favorites: list[Favorite] | None = None) -> None:
        self.favorites: list[Favorite] = list(favorites or [])
        self.next_id = max((f.id for f in self.favorites), default=0) + 1

    async def list_by_user(self, user_id: int) -> list[Favorite]:
        return [f for f in self.favorites if f.user_id == user_id]

    async def get(self, user_id: int, imdb_id: str) -> Favorite | None:
        return next((f for f in self.favorites
                     if f.user_id == user_id and f.imdb_id == imdb_id), None)

    async def add(self, user_id: int, imdb_id: str) -> bool:
        if await self.get(user_id, imdb_id) is not None:
            return False
        self.favorites.append(make_favorite(user_id, imdb_id, movie=make_movie(imdb_id)))
        self.favorites[-1].id = self.next_id
        self.next_id += 1
        return True

    async def remove(self, user_id: int, imdb_id: str) -> None:
        self.favorites = [f for f in self.favorites
                          if not (f.user_id == user_id and f.imdb_id == imdb_id)]


@pytest.fixture
def stale_movie() -> Movie:
    return make_movie(fetched_at=datetime(2020, 1, 1, tzinfo=UTC))
