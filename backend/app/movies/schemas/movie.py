from pydantic import BaseModel, ConfigDict


class MovieRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    imdb_id: str
    title: str
    year: int | None = None
    rating: float | None = None
    poster_url: str | None = None
    description: str | None = None
    genres: list[str] = []
    actors: list[str] = []


class MovieSearchItem(BaseModel):
    imdb_id: str
    title: str | None = None
    year: int | None = None
    actors: str | None = None
    poster_url: str | None = None


class MoodRead(BaseModel):
    key: str
