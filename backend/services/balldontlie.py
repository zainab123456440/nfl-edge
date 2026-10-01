"""BALLDONTLIE NFL API client. Fetch only: no cleaning, no database."""
import time
from typing import Any

import httpx

from config import (
    BALLDONTLIE_API_KEY,
    BDL_BASE_URL,
    MAX_PAGES,
    PER_PAGE,
    REQUEST_TIMEOUT,
)


def _build_params(params: dict[str, Any]) -> list[tuple[str, str]]:
    """Lists become bracket params: {"seasons": [2026]} -> seasons[]=2026"""
    out: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            out.extend((f"{key}[]", str(v)) for v in value)
        else:
            out.append((key, str(value)))
    return out


def _request(path: str, params: dict[str, Any] | None = None, attempt: int = 0) -> dict:
    if not BALLDONTLIE_API_KEY:
        raise RuntimeError("Missing BALLDONTLIE_API_KEY")

    res = httpx.get(
        f"{BDL_BASE_URL}{path}",
        params=_build_params(params or {}),
        headers={"Authorization": BALLDONTLIE_API_KEY},
        timeout=REQUEST_TIMEOUT,
    )

    # Rate limited: back off and retry (1s, 2s, 4s)
    if res.status_code == 429 and attempt < 3:
        time.sleep(2**attempt)
        return _request(path, params, attempt + 1)

    if res.status_code >= 400:
        raise RuntimeError(f"BALLDONTLIE {res.status_code} on {path}: {res.text[:200]}")
    return res.json()


def _paginate(path: str, params: dict[str, Any] | None = None) -> list[dict]:
    """Follow meta.next_cursor until the last page."""
    items: list[dict] = []
    cursor: int | None = None
    for _ in range(MAX_PAGES):
        page = _request(path, {**(params or {}), "per_page": PER_PAGE, "cursor": cursor})
        items.extend(page.get("data", []))
        cursor = (page.get("meta") or {}).get("next_cursor")
        if not cursor:
            break
    return items


# ---------- public fetchers ----------

def fetch_teams() -> list[dict]:
    return _request("/teams").get("data", [])


def fetch_games(season: int) -> list[dict]:
    """All games for a season (regular season + postseason by default)."""
    return _paginate("/games", {"seasons": [season]})


def fetch_odds(season: int, week: int) -> list[dict]:
    """Current odds for every game in a week."""
    odds = _paginate(
        "/odds",
        {
            "season": season,
            "week": week,
        },
    )

    print(
        f"[BALLDONTLIE] odds fetched: "
        f"season={season}, week={week}, rows={len(odds)}"
    )

    if odds:
        print(
            "[BALLDONTLIE] sample:",
            {
                "game_id": odds[0].get("game_id"),
                "vendor": odds[0].get("vendor"),
                "spread_home": odds[0].get("spread_home_value"),
                "moneyline_home": odds[0].get("moneyline_home_odds"),
            },
        )

    return odds


def fetch_opening_odds(season: int, week: int) -> list[dict]:
    """Opening odds (GOAT). Use to backfill the opening line for charts."""
    return _paginate("/odds/opening", {"season": season, "week": week})


def fetch_injuries() -> list[dict]:
    return _paginate("/player_injuries")


def fetch_player_props(game_id: int) -> list[dict]:
    """LIVE props for one game. Not paginated; the API stores no history."""
    return _request("/odds/player_props", {"game_id": game_id}).get("data", [])


# ---------- added for the Props page ----------

def fetch_opening_player_props(game_id: int) -> list[dict]:
    """Opening player props for one game (GOAT). Not paginated."""
    return _request("/odds/player_props/opening", {"game_id": game_id}).get("data", [])


def fetch_active_players() -> list[dict]:
    """Every active NFL player, each with a nested `team`."""
    return _paginate("/players/active")


def fetch_players_by_ids(player_ids: list[int]) -> list[dict]:
    """Look up specific players (100 ids per request)."""
    out: list[dict] = []
    ids = list(player_ids)
    for i in range(0, len(ids), 100):
        out.extend(_paginate("/players", {"player_ids": ids[i : i + 100]}))
    return out