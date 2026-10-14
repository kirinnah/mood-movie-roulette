from fastapi import APIRouter, Response, status

from app.favorites.api.deps import FavoriteServiceDep
from app.favorites.schemas.favorite import FavoriteCreate, FavoriteRead
from app.users.api.deps import CurrentUserDep

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[FavoriteRead])
async def list_favorites(user: CurrentUserDep, service: FavoriteServiceDep):
    return await service.list(user.id)


@router.post("", response_model=FavoriteRead, status_code=status.HTTP_201_CREATED)
async def add_favorite(
    body: FavoriteCreate, response: Response, user: CurrentUserDep, service: FavoriteServiceDep
):
    favorite, created = await service.add(user.id, body.imdb_id)
    if not created:
        response.status_code = status.HTTP_200_OK
    return favorite


@router.delete("/{imdb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(imdb_id: str, user: CurrentUserDep, service: FavoriteServiceDep):
    await service.remove(user.id, imdb_id)
