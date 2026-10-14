from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.movies.schemas.movie import MovieRead


class FavoriteCreate(BaseModel):
    imdb_id: str = Field(pattern=r"^tt\d{5,10}$")


class FavoriteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    movie: MovieRead
