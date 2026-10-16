import asyncio
import logging

import httpx

from app.core.exceptions import NotFoundError, UpstreamError
from app.movies.schemas.imdb import ImdbMovie, ImdbSearchItem

log = logging.getLogger(__name__)

NOT_FOUND_ERRORS = {"incorrect imdb id.", "movie not found!", "series not found!", "too many results."}
FATAL_ERRORS = ("invalid api key", "no api key provided", "request limit reached")


def _na(value: object) -> str | None:
    text = str(value).strip() if value is not None else ""
    return None if text in ("", "N/A") else text


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


def _split(value: object) -> list[str]:
    text = _na(value)
    return [part.strip() for part in text.split(",") if part.strip()] if text else []


def _raise_for_error(error: str) -> None:
    lowered = error.strip().lower()
    if lowered in NOT_FOUND_ERRORS:
        raise NotFoundError("Фильм не найден")
    if lowered.startswith(FATAL_ERRORS):
        raise UpstreamError(f"OMDb отклонил запрос: {error}")
    raise ValueError(f"OMDb: {error}")


class OmdbClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://www.omdbapi.com",
        timeout: float = 5.0,
        retries: int = 3,
        backoff: float = 0.4,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._http = httpx.AsyncClient(base_url=base_url, timeout=timeout, transport=transport)
        self._retries = retries
        self._backoff = backoff

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _get(self, params: dict[str, str]) -> dict:
        last_exc: Exception | None = None
        for attempt in range(1, self._retries + 1):
            try:
                resp = await self._http.get("/", params={**params, "apikey": self._api_key})
                try:
                    data = resp.json()
                except ValueError:
                    data = None
                if isinstance(data, dict) and data.get("Response") == "False":
                    _raise_for_error(str(data.get("Error", "")))
                resp.raise_for_status()
                if not isinstance(data, dict):
                    raise ValueError("ответ OMDb не JSON-объект")
                return data
            except (httpx.HTTPError, ValueError) as exc:
                last_exc = exc
                log.warning("OMDb API error (attempt %s/%s): %s", attempt, self._retries, exc)
                if attempt < self._retries:
                    await asyncio.sleep(self._backoff * attempt)
        raise UpstreamError("OMDb API недоступен") from last_exc

    async def get_movie(self, imdb_id: str) -> ImdbMovie:
        data = await self._get({"i": imdb_id, "plot": "short"})
        title = _na(data.get("Title"))
        if not title:
            raise NotFoundError("Фильм не найден")
        return ImdbMovie(
            imdb_id=imdb_id,
            title=title,
            year=_year(data.get("Year")),
            rating=_float(_na(data.get("imdbRating"))),
            poster_url=_na(data.get("Poster")),
            description=_na(data.get("Plot")),
            genres=_split(data.get("Genre")),
            actors=_split(data.get("Actors")),
        )

    async def search(self, query: str) -> list[ImdbSearchItem]:
        try:
            data = await self._get({"s": query, "type": "movie"})
        except NotFoundError:
            return []
        return [
            ImdbSearchItem(
                imdb_id=item["imdbID"],
                title=item.get("Title"),
                year=_year(item.get("Year")),
                actors=None,
                poster_url=_na(item.get("Poster")),
            )
            for item in data.get("Search") or []
            if str(item.get("imdbID", "")).startswith("tt")
        ]
