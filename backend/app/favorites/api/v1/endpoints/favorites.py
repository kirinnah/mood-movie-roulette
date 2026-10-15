from fastapi import APIRouter, Response, status

from app.favorites.api.deps import FavoriteServiceDep
from app.favorites.schemas import FavoriteCreate, FavoriteRead
from app.users.api.deps import CurrentUserDep

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("")
async def list_favorites(user: CurrentUserDep, service: FavoriteServiceDep) -> list[FavoriteRead]:
    return [FavoriteRead.model_validate(f) for f in await service.list(user.id)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_favorite(
    body: FavoriteCreate, response: Response, user: CurrentUserDep, service: FavoriteServiceDep
) -> FavoriteRead:
    favorite, created = await service.add(user.id, body.imdb_id)
    if not created:
        response.status_code = status.HTTP_200_OK  # идемпотентный повтор
    return FavoriteRead.model_validate(favorite)


@router.delete("/{imdb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(imdb_id: str, user: CurrentUserDep, service: FavoriteServiceDep) -> None:
    await service.remove(user.id, imdb_id)
