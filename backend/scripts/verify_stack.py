import argparse
import sys
import uuid

import httpx

PASSWORD = "password123"


def main(base: str) -> int:
    client = httpx.Client(base_url=f"{base}/api/v1", timeout=30)
    failures: list[str] = []

    def check(ok: bool, title: str, detail: object = "") -> bool:
        print(f"{'PASS' if ok else 'FAIL'}  {title}" + ("" if ok else f"   -> {detail}"))
        if not ok:
            failures.append(title)
        return ok

    def auth(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    try:
        health = httpx.get(f"{base}/health", timeout=10)
    except httpx.HTTPError as exc:
        print(f"FAIL  сервер не отвечает на {base}: {exc}\nЗапущен ли uvicorn?")
        return 1
    check(health.status_code == 200, "GET /health", health.text)

    moods = [m["key"] for m in client.get("/moods").json()]
    check(len(moods) >= 1, f"GET /moods: {len(moods)} настроений")

    first_id = None
    for mood in moods:
        r = client.get("/roulette", params={"mood": mood})
        ok = r.status_code == 200 and r.json().get("title") and r.json()["imdb_id"].startswith("tt")
        check(
            bool(ok),
            f"рулетка [{mood}]: {r.json().get('title') if ok else ''}",
            f"{r.status_code} {r.text[:150]}",
        )
        if ok and first_id is None:
            first_id = r.json()["imdb_id"]
    check(
        client.get("/roulette", params={"mood": "no-such-mood"}).status_code == 404,
        "неизвестное настроение -> 404",
    )

    if first_id:
        r = client.get(f"/movies/{first_id}")
        check(
            r.status_code == 200 and r.json()["imdb_id"] == first_id, f"GET /movies/{first_id}", r.text[:150]
        )
    r = client.get("/movies/search", params={"q": "matrix"})
    check(
        r.status_code == 200 and len(r.json()) > 0,
        "поиск по названию (внешний API)",
        f"{r.status_code} {r.text[:150]}",
    )

    email = f"check-{uuid.uuid4().hex[:8]}@example.com"
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    check(
        r.status_code == 201 and r.json()["email"] == email,
        "регистрация -> 201 (запись в БД)",
        f"{r.status_code} {r.text[:150]}",
    )
    r = client.post("/auth/register", json={"email": email, "password": PASSWORD})
    check(r.status_code == 409, "повторная регистрация -> 409", r.status_code)
    r = client.post("/auth/login", data={"username": email, "password": "wrong-password"})
    check(r.status_code == 401, "логин с неверным паролем -> 401", r.status_code)
    r = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    token = r.json().get("access_token", "") if r.status_code == 200 else ""
    check(bool(token), "логин -> токен", f"{r.status_code} {r.text[:150]}")
    if not token:
        print("\nДальше без токена идти нельзя.")
        return 1
    r = client.get("/users/me", headers=auth(token))
    check(r.status_code == 200 and r.json()["email"] == email, "GET /users/me", r.status_code)

    check(client.get("/favorites").status_code == 401, "избранное без токена -> 401")
    movie = first_id or "tt0111161"
    r = client.post("/favorites", json={"imdb_id": movie}, headers=auth(token))
    check(
        r.status_code == 201 and r.json()["movie"]["imdb_id"] == movie,
        f"добавить {movie} в избранное -> 201",
        f"{r.status_code} {r.text[:150]}",
    )
    r = client.post("/favorites", json={"imdb_id": movie}, headers=auth(token))
    check(r.status_code == 200, "повторное добавление -> 200 (идемпотентно)", r.status_code)
    r = client.get("/favorites", headers=auth(token))
    check(
        r.status_code == 200 and [f["movie"]["imdb_id"] for f in r.json()] == [movie],
        "список избранного (чтение из БД)",
        r.text[:150],
    )

    other = f"check-{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": other, "password": PASSWORD})
    other_token = (
        client.post("/auth/login", data={"username": other, "password": PASSWORD})
        .json()
        .get("access_token", "")
    )
    check(
        client.get("/favorites", headers=auth(other_token)).json() == [],
        "чужое избранное не видно другому пользователю",
    )
    client.delete(f"/favorites/{movie}", headers=auth(other_token))
    check(
        len(client.get("/favorites", headers=auth(token)).json()) == 1, "чужое удаление не трогает мои записи"
    )
    r = client.delete(f"/favorites/{movie}", headers=auth(token))
    check(
        r.status_code == 204 and client.get("/favorites", headers=auth(token)).json() == [],
        "удаление из избранного -> 204",
        r.status_code,
    )

    print(f"\nИтого: {'всё работает' if not failures else f'провалено проверок: {len(failures)}'}")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8000")
    sys.exit(main(parser.parse_args().base))
