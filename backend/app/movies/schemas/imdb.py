from pydantic import BaseModel


class ImdbMovie(BaseModel):
    imdb_id: str
    title: str
    year: int | None = None
    rating: float | None = None
    poster_url: str | None = None
    description: str | None = None
    genres: list[str] = []
    actors: list[str] = []


class ImdbSearchItem(BaseModel):
    imdb_id: str
    title: str | None = None
    year: int | None = None
    actors: str | None = None
    poster_url: str | None = None
