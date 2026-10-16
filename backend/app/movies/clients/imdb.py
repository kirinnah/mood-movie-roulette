import asyncio
import logging

import httpx

from app.core.exceptions import NotFoundError, UpstreamError
from app.movies.schemas.imdb import ImdbMovie, ImdbSearchItem

log = logging.getLogger(__name__)


def _year(value: object) -> int | None:
    try:
        return int(str(value)[:4])
    except (TypeError, ValueError):
        return None


def _float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


class ImdbClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        retries: int = 3,
        backoff: float = 0.4,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._http = httpx.AsyncClient(base_url=base_url, timeout=timeout, transport=transport)
        self._retries = retries
        self._backoff = backoff

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get(self, params: dict[str, str]) -> dict:
        """Публичный IMDbOT нестабилен, поэтому сбои (сеть, таймаут, HTTP-ошибка, битый JSON) повторяем."""
        last_exc: Exception | None = None
        for attempt in range(1, self._retries + 1):
            try:
                resp = await self._http.get("/search", params=params)
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_exc = exc
                log.warning("IMDb API error (attempt %s/%s): %s", attempt, self._retries, exc)
                if attempt < self._retries:
                    await asyncio.sleep(self._backoff * attempt)
        raise UpstreamError("IMDb API недоступен") from last_exc

    async def get_movie(self, imdb_id: str) -> ImdbMovie:
        short = (await self._get({"tt": imdb_id})).get("short") or {}
        if not short.get("name"):
            raise NotFoundError("Фильм не найден")

        genres = short.get("genre") or []
        if isinstance(genres, str):
            genres = [genres]
        actors = [a["name"] for a in short.get("actor") or [] if isinstance(a, dict) and a.get("name")]

        return ImdbMovie(
            imdb_id=imdb_id,
            title=short["name"],
            year=_year(short.get("datePublished")),
            rating=_float((short.get("aggregateRating") or {}).get("ratingValue")),
            poster_url=short.get("image"),
            description=short.get("description"),
            genres=genres,
            actors=actors,
        )

    async def search(self, query: str) -> list[ImdbSearchItem]:
        data = await self._get({"q": query})
        return [
            ImdbSearchItem(
                imdb_id=item["#IMDB_ID"],
                title=item.get("#TITLE"),
                year=_year(item.get("#YEAR")),
                actors=item.get("#ACTORS"),
                poster_url=item.get("#IMG_POSTER"),
            )
            for item in data.get("description") or []
            if str(item.get("#IMDB_ID", "")).startswith("tt")
        ]