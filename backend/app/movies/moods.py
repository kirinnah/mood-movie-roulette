from dataclasses import dataclass

from app.core.exceptions import NotFoundError


@dataclass(frozen=True, slots=True)
class Mood:
    key: str
    imdb_ids: tuple[str, ...]


_MOODS = (
    Mood(
        "happy",
        (
            "tt0107048",
            "tt0087332",
            "tt0109686",
            "tt0829482",
            "tt0088763",
            "tt0093779",
            "tt1675434",
            "tt0211915",
            "tt2278388",
            "tt0118715",
        ),
    ),
    Mood(
        "sad",
        (
            "tt0118799",
            "tt0120689",
            "tt0109830",
            "tt0095327",
            "tt1049413",
            "tt0253474",
            "tt0108052",
            "tt0120338",
            "tt0332280",
            "tt0097165",
        ),
    ),
    Mood(
        "cozy",
        (
            "tt0245429",
            "tt0347149",
            "tt0382932",
            "tt2380307",
            "tt0910970",
            "tt0114709",
            "tt0110357",
            "tt0092067",
            "tt0095765",
            "tt0112471",
        ),
    ),
    Mood(
        "adventure",
        (
            "tt0082971",
            "tt0097576",
            "tt0325980",
            "tt0107290",
            "tt1392190",
            "tt0095016",
            "tt0103064",
            "tt0076759",
            "tt0120737",
            "tt0172495",
        ),
    ),
    Mood(
        "scary",
        (
            "tt0078748",
            "tt0081505",
            "tt0084787",
            "tt1457767",
            "tt7784604",
            "tt0102926",
            "tt0114369",
            "tt0070047",
            "tt0054215",
            "tt1130884",
        ),
    ),
    Mood(
        "thoughtful",
        (
            "tt1375666",
            "tt0816692",
            "tt0083658",
            "tt0209144",
            "tt0338013",
            "tt0137523",
            "tt0120382",
            "tt0482571",
            "tt0062622",
            "tt0133093",
        ),
    ),
    Mood(
        "romantic",
        (
            "tt0332280",
            "tt0098635",
            "tt0112471",
            "tt0381681",
            "tt0211915",
            "tt0118694",
            "tt0120338",
            "tt0034583",
            "tt0338013",
            "tt0118799",
        ),
    ),
)
MOODS: dict[str, Mood] = {m.key: m for m in _MOODS}


def get_mood(key: str) -> Mood:
    try:
        return MOODS[key]
    except KeyError:
        raise NotFoundError(f"Неизвестное настроение: {key}") from None
