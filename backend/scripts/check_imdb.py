import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import AppError, settings  # noqa: E402
from app.movies.clients import create_movie_client  # noqa: E402
from app.movies.moods import MOODS  # noqa: E402

OPTIONAL_FIELDS = ("year", "rating", "poster_url", "description", "genres", "actors")


RAW_PARAMS = {"imdbot": ({"tt": "{id}"}, {"q": "matrix"}), "omdb": ({"i": "{id}"}, {"s": "matrix"})}


async def dump_raw_samples(client: Any, imdb_id: str) -> None:
    by_id, by_query = RAW_PARAMS[settings.movie_provider]
    for name, params in (("tt", {k: v.format(id=imdb_id) for k, v in by_id.items()}), ("search", by_query)):
        try:
            data = await client._get(params)  # noqa: SLF001
        except AppError as exc:
            print(f"  не удалось сохранить сырой ответ ({name}): {exc.detail} [{exc.__cause__}]")
            continue
        path = Path(f"imdb_sample_{name}.json")
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  сырой ответ сохранён: {path}")


async def main(warm: bool, limit: int | None) -> int:
    ids = list(dict.fromkeys(i for mood in MOODS.values() for i in mood.imdb_ids))[:limit]
    client = create_movie_client()
    print(f"Провайдер: {settings.movie_provider} | фильмов к проверке: {len(ids)}\n")

    await dump_raw_samples(client, ids[0])

    print("\nПоиск по названию:")
    try:
        found = await client.search("matrix")
        print(f"  найдено {len(found)}; первый: {found[0].title if found else '-'}")
    except AppError as exc:
        print(f"  FAIL: {exc.detail} [{exc.__cause__}]")

    print("\nКарточки фильмов:")
    loaded, failed = {}, []
    for n, imdb_id in enumerate(ids, 1):
        try:
            movie = await client.get_movie(imdb_id)
        except AppError as exc:
            failed.append(imdb_id)
            print(f"  [{n:02}/{len(ids)}] FAIL {imdb_id}: {exc.detail} [{exc.__cause__}]")
        else:
            loaded[imdb_id] = movie
            empty = [f for f in OPTIONAL_FIELDS if not getattr(movie, f)]
            note = f"  (пусто: {', '.join(empty)})" if empty else ""
            print(f"  [{n:02}/{len(ids)}] OK   {imdb_id}: {movie.title} ({movie.year}) {movie.rating}{note}")
        await asyncio.sleep(0.3)

    print("\nПо настроениям (загружено / в пуле):")
    for mood in MOODS.values():
        pool = [i for i in mood.imdb_ids if i in ids]
        got = sum(1 for i in pool if i in loaded)
        flag = "  <-- мало, рулетка может падать" if pool and got < 3 else ""
        print(f"  {mood.key:<11} {got}/{len(pool)}{flag}")

    if warm and loaded:
        from app.core.db.session import session_factory
        from app.movies.repositories import MovieRepository

        async with session_factory() as session:
            repo = MovieRepository(session)
            for movie in loaded.values():
                await repo.upsert(movie)
            await session.commit()
        print(f"\nКэш прогрет: в БД записано фильмов: {len(loaded)}")

    await client.aclose()
    print(f"\nИтого: успешно {len(loaded)}, ошибок {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--warm", action="store_true", help="записать загруженные фильмы в БД")
    parser.add_argument("--limit", type=int, default=None, help="проверить только первые N фильмов")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.warm, args.limit)))
