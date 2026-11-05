# Тестирование backend

Тесты лежат в `backend/tests/` и пишутся с нуля под существующий код (`app/` не меняется).

## Установка и запуск

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.txt   # Windows
pytest                                                        # весь набор
pytest -m integration                                         # только Postgres-интеграционные
ruff check tests/
```

Unit- и API-тесты не требуют ни БД, ни сети: внешний API подменяется
`httpx.MockTransport` (клиенты) и фейками-провайдерами/репозиториями (сервисы),
HTTP-слой гоняется через `httpx.ASGITransport` с подменёнными зависимостями.

Интеграционные тесты (`test_integration_pg.py`) требуют настоящий PostgreSQL и
DSN тестовой БД, иначе пропускаются:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://roulette:roulette@localhost:5432/roulette_test pytest
```

## Структура

| Файл | Что покрывает |
|---|---|
| `test_settings.py` | `Settings.validate_runtime()`: пустой, короткий, устаревший секреты |
| `test_clients_omdb.py` | OMDb-клиент: маппинг полей, `N/A`, ошибки, ретраи (без сети) |
| `test_clients_imdb.py` | IMDbOT-клиент: вложенный JSON, ретраи, 404 (без сети) |
| `test_services_movies.py` | кэш фильмов: свежий, устаревший, API недоступен |
| `test_services_roulette.py` | рулетка: `exclude`, неизвестное настроение, фолбэк из кэша |
| `test_services_users.py` | регистрация/логин: email в нижний регистр, 409, токены, граница 72 байта bcrypt |
| `test_services_favorites.py` | избранное: повторное добавление не ошибка, чужие записи не видны |
| `test_api.py` | HTTP-слой: статусы 200/201/204/401/404/409/422/502, валидация, health |
| `test_integration_pg.py` | реальный Postgres: upsert, ON CONFLICT, сквозные сценарии эндпоинтов |

`conftest.py` выставляет `MOVIE_PROVIDER=imdbot` и тестовый `JWT_SECRET` до
импорта приложения, чтобы тесты не зависели от локального `.env`, и содержит
фейки (`FakeMovieProvider`, `FakeMovieRepository`, `FakeUserRepository`,
`FakeFavoriteRepository`), которые подставляются через конструкторы сервисов.

## Что проверяют граничные тесты

- пароль 8–72 символа: 7 и 73 символа → 422;
- просроченный JWT → 401;
- поисковый запрос короче 2 символов → 422;
- `GET /health` → 503 при недоступной БД;
- повторное добавление в избранное → 200, а не ошибка;
- рулетка: 404 при неизвестном настроении, 502 когда внешний API лежит и кэш пуст.

## Известные проблемы

- `DELETE /favorites/{imdb_id}` возвращает 204, но commit сессии происходит
  после отправки ответа, поэтому следующий `GET /favorites` ещё возвращает
  фильм. Фиксится на стороне бэкенда (`get_session` в `app/core/db/session.py`);
  репозиторный уровень удаления при этом работает корректно.
