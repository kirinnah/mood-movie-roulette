from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.db.session import engine
from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    UpstreamError,
)
from app.favorites.api.v1.router import router as favorites_router
from app.movies.api.v1.router import router as movies_router
from app.movies.clients.imdb import ImdbClient
from app.users.api.v1.router import router as users_router


STATUS_BY_ERROR: dict[type[AppError], int] = {
    NotFoundError: 404,
    ConflictError: 409,
    UnauthorizedError: 401,
    UpstreamError: 502,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.imdb_client = ImdbClient(settings.imdb_api_base, settings.imdb_timeout)
    yield
    await app.state.imdb_client.aclose()
    await engine.dispose()


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    status_code = next((code for cls, code in STATUS_BY_ERROR.items() if isinstance(exc, cls)), 500)
    headers = {"WWW-Authenticate": "Bearer"} if isinstance(exc, UnauthorizedError) else None
    return JSONResponse(status_code=status_code, content={"detail": exc.detail}, headers=headers)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.3.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
    )
    app.add_exception_handler(AppError, app_error_handler)

    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(users_router)
    api_v1.include_router(movies_router)
    api_v1.include_router(favorites_router)
    app.include_router(api_v1)

    @app.get("/health", tags=["service"])
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
