"""Turns BALLDONTLIE responses into the exact row shape of our Supabase tables."""
import math
from datetime import datetime, timezone
from typing import Any, Iterator


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_num(value: Any) -> float | None:
    """Convert a value to a finite float. Invalid values become None."""
    if value is None or value == "":
        return None

    try:
        n = float(value)
    except (TypeError, ValueError):
        return None

    return n if math.isfinite(n) else None


def to_int(value: Any) -> int | None:
    """Convert odds/price values to int when possible."""
    if value is None or value == "":
        return None

    try:
        n = int(value)
    except (TypeError, ValueError):
        return None

    return n


def chunk(items: list, size: int) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


# NOTE: odds_api_name is intentionally NOT included.
def normalize_team(t: dict) -> dict:
    return {
        "id": t["id"],
        "name": t["full_name"],
        "city": t.get("location"),
        "abbreviation": t["abbreviation"],
        "conference": t.get("conference"),
        "division": t.get("division"),
        "updated_at": now_iso(),
    }


# NOTE: odds_api_event_id is intentionally NOT included.
def normalize_game(g: dict) -> dict | None:
    if not g.get("date"):
        return None

    home_team = g.get("home_team") or {}
    away_team = g.get("visitor_team") or {}

    if not home_team.get("id") or not away_team.get("id"):
        return None

    if not g.get("id"):
        return None

    return {
        "id": g["id"],
        "season": g["season"],
        "week": g.get("week"),
        "home_team_id": home_team["id"],
        "away_team_id": away_team["id"],
        "kickoff_at": g["date"],
        "status": g.get("status_state") or "scheduled",
        "home_score": g.get("home_team_score"),
        "away_score": g.get("visitor_team_score"),
        "venue": g.get("venue"),
        "updated_at": now_iso(),
    }


def normalize_odd(o: dict) -> list[dict]:
    """
    Convert one BALLDONTLIE sportsbook/game record
    into multiple Supabase odds rows.

    Supported:
      - spreads
      - totals
      - h2h / moneyline
    """

    game_id = o.get("game_id")
    vendor = o.get("vendor")

    if not game_id:
        return []

    if not vendor:
        return []

    captured_at = (
        o.get("updated_at")
        or o.get("opened_at")
        or now_iso()
    )

    rows: list[dict] = []

    def push(
        market: str,
        outcome: str,
        line: float | None,
        price: int | None,
    ) -> None:
        if price is None:
            return

        rows.append(
            {
                "game_id": game_id,
                "book": str(vendor).lower().strip(),
                "market": market,
                "outcome": outcome,
                "line": line,
                "price": price,
                "captured_at": captured_at,
            }
        )

    # Spreads
    push(
        "spreads",
        "home",
        to_num(o.get("spread_home_value")),
        to_int(o.get("spread_home_odds")),
    )

    push(
        "spreads",
        "away",
        to_num(o.get("spread_away_value")),
        to_int(o.get("spread_away_odds")),
    )

    # Totals
    total = to_num(o.get("total_value"))

    push(
        "totals",
        "over",
        total,
        to_int(o.get("total_over_odds")),
    )

    push(
        "totals",
        "under",
        total,
        to_int(o.get("total_under_odds")),
    )

    # Moneyline
    push(
        "h2h",
        "home",
        None,
        to_int(o.get("moneyline_home_odds")),
    )

    push(
        "h2h",
        "away",
        None,
        to_int(o.get("moneyline_away_odds")),
    )

    return rows


# Returns None when the feed has no team for the player.
def normalize_injury(i: dict) -> dict | None:
    player = i.get("player") or {}
    team = player.get("team")

    if not player.get("id") or not team:
        return None

    return {
        "player_id": player["id"],
        "player_name": (
            f"{player.get('first_name', '')} "
            f"{player.get('last_name', '')}"
        ).strip(),
        "position": player.get("position_abbreviation"),
        "team_id": team["id"],
        "status": i.get("status") or "Unknown",
        "description": i.get("comment"),
        "reported_at": i.get("date"),
    }