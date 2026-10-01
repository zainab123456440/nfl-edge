"""Supabase reads for the DFS lineup engine. Same style as props_queries.py."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from db import get_db

PAGE = 1000
CHUNK = 150  # ids per .in_() call (keeps the request URL short)

# DraftKings abbreviation -> abbreviations your teams table may use instead
TEAM_ALIASES = {
    "JAX": ["JAC"], "WAS": ["WSH"], "LAR": ["LA"], "LA": ["LAR"],
    "ARI": ["ARZ"], "LV": ["LVR", "OAK"], "KC": ["KAN"], "NE": ["NWE"],
    "NO": ["NOR"], "SF": ["SFO"], "TB": ["TAM"], "GB": ["GNB"],
}


def _chunks(items: list, size: int = CHUNK):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _parse_ts(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def get_teams() -> tuple[dict, dict]:
    """Returns (abbreviation -> id, id -> abbreviation)."""
    rows = get_db().table("teams").select("id,abbreviation").limit(100).execute().data or []
    by_abbr = {r["abbreviation"].upper(): r["id"] for r in rows if r.get("abbreviation")}
    by_id = {v: k for k, v in by_abbr.items()}
    return by_abbr, by_id


def resolve_team_id(abbr: str, by_abbr: dict) -> Optional[int]:
    abbr = abbr.upper()
    if abbr in by_abbr:
        return by_abbr[abbr]
    for alt in TEAM_ALIASES.get(abbr, []):
        if alt in by_abbr:
            return by_abbr[alt]
    return None


def find_game(home_id: int, away_id: int, kickoff_utc: datetime, window_hours: int = 12) -> list:
    """Games between these two teams near the kickoff time (closest first)."""
    lo = (kickoff_utc - timedelta(hours=window_hours)).astimezone(timezone.utc).isoformat()
    hi = (kickoff_utc + timedelta(hours=window_hours)).astimezone(timezone.utc).isoformat()
    rows = (
        get_db().table("games")
        .select("id,status,kickoff_at,home_team_id,away_team_id")
        .eq("home_team_id", home_id).eq("away_team_id", away_id)
        .gte("kickoff_at", lo).lte("kickoff_at", hi)
        .limit(10).execute().data or []
    )
    rows.sort(key=lambda g: abs((_parse_ts(g["kickoff_at"]) - kickoff_utc).total_seconds()))
    return rows


def props_player_ids(game_id: int) -> set:
    ids, start = set(), 0
    while True:
        batch = (
            get_db().table("props_current").select("player_id")
            .eq("game_id", game_id).order("id").range(start, start + PAGE - 1)
            .execute().data or []
        )
        ids.update(r["player_id"] for r in batch if r.get("player_id") is not None)
        if len(batch) < PAGE:
            return ids
        start += PAGE


def players_by_ids(ids: list) -> list:
    out = []
    for chunk in _chunks(list(ids)):
        out += (
            get_db().table("players").select("id,name,position,team_id,is_active")
            .in_("id", chunk).execute().data or []
        )
    return out


def roster_players(team_ids: list) -> list:
    return (
        get_db().table("players").select("id,name,position,team_id,is_active")
        .in_("team_id", team_ids).eq("is_active", True).limit(PAGE).execute().data or []
    )


def game_odds(game_id: int) -> list:
    """Recent odds_snapshots rows for the game, with timestamps parsed."""
    rows = (
        get_db().table("odds_snapshots")
        .select("book,market,outcome,line,price,captured_at")
        .eq("game_id", game_id).order("captured_at", desc=True).limit(PAGE)
        .execute().data or []
    )
    for r in rows:
        r["captured_at"] = _parse_ts(r["captured_at"])
    return rows


def latest_injury_rows(player_ids: list) -> list:
    """Reads the latest_injuries view (same one the props page uses)."""
    out = []
    try:
        for chunk in _chunks(list(player_ids)):
            out += (
                get_db().table("latest_injuries").select("player_id,status")
                .in_("player_id", chunk).execute().data or []
            )
    except Exception as e:  # never break lineup analysis over injuries
        print(f"injury lookup skipped: {e}")
    return out


def game_props(game_id: int) -> dict:
    """All current prop lines for the game, grouped as
    {player_id: {market: [{line, over_odds, under_odds, book}, ...]}}."""
    out: dict = {}
    start = 0
    while True:
        batch = (
            get_db().table("props_current")
            .select("player_id,market,line,over_odds,under_odds,bookmakers!inner(key)")
            .eq("game_id", game_id).order("id").range(start, start + PAGE - 1)
            .execute().data or []
        )
        for r in batch:
            b = r.pop("bookmakers", None) or {}
            row = {"line": r.get("line"), "over_odds": r.get("over_odds"),
                   "under_odds": r.get("under_odds"), "book": b.get("key")}
            out.setdefault(r["player_id"], {}).setdefault(r["market"], []).append(row)
        if len(batch) < PAGE:
            return out
        start += PAGE