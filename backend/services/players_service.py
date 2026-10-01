"""Players sync: BALLDONTLIE -> players table.

players.id is the BALLDONTLIE player id (same pattern as teams.id and games.id),
so props, injuries and stats all join on one id with no name matching.
"""
import logging

from config import DB_BATCH_SIZE
from db import get_db
from services.balldontlie import fetch_active_players, fetch_players_by_ids
from services.normalize import chunk

logger = logging.getLogger(__name__)


def normalize_player(p: dict, valid_team_ids: set[int]) -> dict | None:
    if not p.get("id"):
        return None
    first = (p.get("first_name") or "").strip()
    last = (p.get("last_name") or "").strip()
    team_id = (p.get("team") or {}).get("id")
    return {
        "id": p["id"],
        "balldontlie_id": p["id"],
        "name": f"{first} {last}".strip(),
        "first_name": first or None,
        "last_name": last or None,
        "position": p.get("position_abbreviation") or p.get("position"),
        "team_id": team_id if team_id in valid_team_ids else None,
        "jersey_number": p.get("jersey_number"),
        "is_active": True,
    }


def _valid_team_ids() -> set[int]:
    rows = get_db().table("teams").select("id").execute().data or []
    return {r["id"] for r in rows}


def _upsert(rows: list[dict]) -> None:
    for batch in chunk(rows, DB_BATCH_SIZE):
        get_db().table("players").upsert(batch, on_conflict="id").execute()


def sync_players() -> dict:
    """Run daily (and once before the first props refresh). Needs teams synced first."""
    teams = _valid_team_ids()
    if not teams:
        return {"ok": False, "error": "teams table is empty; run /api/cron/sync-games first"}

    rows = [r for r in (normalize_player(p, teams) for p in fetch_active_players()) if r]
    _upsert(rows)
    return {"ok": True, "players_upserted": len(rows)}


def ensure_players(player_ids: set[int]) -> set[int]:
    """Fetch and store any player ids we don't have yet. Returns the ids now present."""
    if not player_ids:
        return set()
    teams = _valid_team_ids()
    try:
        rows = [
            r
            for r in (normalize_player(p, teams) for p in fetch_players_by_ids(sorted(player_ids)))
            if r
        ]
        _upsert(rows)
    except Exception:
        logger.exception("ensure_players failed")
        return set()
    return {r["id"] for r in rows}