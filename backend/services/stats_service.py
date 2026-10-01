"""Stats sync: BALLDONTLIE -> player_game_logs and player_season_stats.

These tables power hit rates and recent-form charts on the Props page.
Only fantasy-relevant players are stored (QB/RB/FB/WR/TE/K, or anyone with
offensive/kicking stats). Pure defenders are skipped: no props exist for them.

Known limit: BALLDONTLIE lists a player in /stats only if he recorded stats,
so a game where a receiver had no targets may be missing from his log.
"""
import logging

from config import DB_BATCH_SIZE, NFL_SEASON
from db import get_db
from services.balldontlie import fetch_season_stats, fetch_stats_for_games
from services.normalize import chunk
from services.players_service import store_players

logger = logging.getLogger(__name__)

PROP_POSITIONS = {"QB", "RB", "FB", "WR", "TE", "K", "PK"}
GAMES_PER_REQUEST = 3
DEFAULT_SCAN = 20  # newest final games checked on a normal run


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _n(v) -> int:
    try:
        return int(round(float(v))) if v is not None else 0
    except (TypeError, ValueError):
        return 0


def _relevant(row: dict, att_keys: tuple) -> bool:
    player = row.get("player") or {}
    if (player.get("position_abbreviation") or "").upper() in PROP_POSITIONS:
        return True
    return any(_n(row.get(k)) > 0 for k in att_keys)


_GAME_ATT_KEYS = ("passing_attempts", "rushing_attempts", "receiving_targets", "receptions", "field_goal_attempts")
_SEASON_ATT_KEYS = ("passing_attempts", "rushing_attempts", "receiving_targets", "receptions")


def normalize_log(row: dict) -> dict | None:
    player, team, game = row.get("player") or {}, row.get("team") or {}, row.get("game") or {}
    if not player.get("id") or not game.get("id") or not team.get("id"):
        return None

    home_id = (game.get("home_team") or {}).get("id")
    visitor_id = (game.get("visitor_team") or {}).get("id")
    is_home = team["id"] == home_id
    opponent_id = visitor_id if is_home else home_id
    solo = _n(row.get("solo_tackles"))
    total = _n(row.get("total_tackles"))

    return {
        "player_id": player["id"],
        "game_id": game["id"],
        "season": game.get("season"),
        "week": game.get("week"),
        "game_date": (game.get("date") or "")[:10] or None,
        "team_id": team["id"],
        "opponent_team_id": opponent_id,
        "is_home": is_home,
        "played": True,
        "pass_att": _n(row.get("passing_attempts")),
        "pass_cmp": _n(row.get("passing_completions")),
        "pass_yds": _n(row.get("passing_yards")),
        "pass_td": _n(row.get("passing_touchdowns")),
        "pass_int": _n(row.get("passing_interceptions")),
        "sacks_taken": _n(row.get("sacks")),
        "rush_att": _n(row.get("rushing_attempts")),
        "rush_yds": _n(row.get("rushing_yards")),
        "rush_td": _n(row.get("rushing_touchdowns")),
        "rush_long": _n(row.get("long_rushing")),
        "targets": _n(row.get("receiving_targets")),
        "receptions": _n(row.get("receptions")),
        "rec_yds": _n(row.get("receiving_yards")),
        "rec_td": _n(row.get("receiving_touchdowns")),
        "rec_long": _n(row.get("long_reception")),
        "fumbles": _n(row.get("fumbles")),
        "fumbles_lost": _n(row.get("fumbles_lost")),
        "fg_att": _n(row.get("field_goal_attempts")),
        "fg_made": _n(row.get("field_goals_made")),
        "xp_made": _n(row.get("extra_points_made")),
        "tackles_solo": solo,
        "tackles_assist": max(total - solo, 0),
        "sacks": _n(row.get("defensive_sacks")),
        "def_int": _n(row.get("defensive_interceptions")),
    }


def normalize_season(row: dict, season: int) -> dict | None:
    player = row.get("player") or {}
    if not player.get("id"):
        return None
    return {
        "player_id": player["id"],
        "season": season,
        "games_played": _n(row.get("games_played")),
        "pass_att": _n(row.get("passing_attempts")),
        "pass_cmp": _n(row.get("passing_completions")),
        "pass_yds": _n(row.get("passing_yards")),
        "pass_td": _n(row.get("passing_touchdowns")),
        "pass_int": _n(row.get("passing_interceptions")),
        "rush_att": _n(row.get("rushing_attempts")),
        "rush_yds": _n(row.get("rushing_yards")),
        "rush_td": _n(row.get("rushing_touchdowns")),
        "targets": _n(row.get("receiving_targets")),
        "receptions": _n(row.get("receptions")),
        "rec_yds": _n(row.get("receiving_yards")),
        "rec_td": _n(row.get("receiving_touchdowns")),
    }


def _existing_player_ids(ids: list[int]) -> set[int]:
    found: set[int] = set()
    for batch in chunk(ids, 200):
        rows = get_db().table("players").select("id").in_("id", batch).execute().data or []
        found.update(r["id"] for r in rows)
    return found


def _ensure_players(rows: list[dict]) -> set[int]:
    """Store nested players we don't have yet; returns every player id now available."""
    nested = {r["player"]["id"]: r["player"] for r in rows if (r.get("player") or {}).get("id")}
    have = _existing_player_ids(list(nested))
    missing = [p for pid, p in nested.items() if pid not in have]
    if missing:
        store_players(missing)
        have = _existing_player_ids(list(nested))
    return have


# ---------------------------------------------------------------------
# Game logs
# ---------------------------------------------------------------------
def _has_logs(game_id: int) -> bool:
    res = get_db().table("player_game_logs").select("id").eq("game_id", game_id).limit(1).execute()
    return bool(res.data)


def _games_needing_logs(season: int, limit: int, scan: int | None) -> list[int]:
    finals = (
        get_db()
        .table("games")
        .select("id,kickoff_at")
        .eq("season", season)
        .eq("status", "final")
        .order("kickoff_at", desc=True)
        .limit(500)
        .execute()
        .data
        or []
    )
    if scan:
        finals = finals[:scan]
    needed: list[int] = []
    for g in finals:
        if not _has_logs(g["id"]):
            needed.append(g["id"])
            if len(needed) >= limit:
                break
    return needed


def sync_game_logs(season: int = NFL_SEASON, max_games: int = 10, backfill: bool = False) -> dict:
    """Store logs for finished games that don't have them yet.

    Normal run scans the newest 20 final games. backfill=true scans the whole
    season; call it repeatedly until games_synced is 0.
    """
    game_ids = _games_needing_logs(season, max_games, None if backfill else DEFAULT_SCAN)
    summary = {"games_synced": 0, "log_rows": 0, "skipped_defense": 0, "errors": []}

    for batch_ids in chunk(game_ids, GAMES_PER_REQUEST):
        try:
            raw = fetch_stats_for_games(batch_ids)
            relevant = [r for r in raw if _relevant(r, _GAME_ATT_KEYS)]
            summary["skipped_defense"] += len(raw) - len(relevant)

            available = _ensure_players(relevant)
            logs = [
                n
                for n in (normalize_log(r) for r in relevant)
                if n and n["player_id"] in available
            ]
            for rows in chunk(logs, DB_BATCH_SIZE):
                get_db().table("player_game_logs").upsert(rows, on_conflict="player_id,game_id").execute()
            summary["games_synced"] += len(batch_ids)
            summary["log_rows"] += len(logs)
        except Exception as e:
            logger.exception("game log sync failed for games %s", batch_ids)
            summary["errors"].append(f"games {batch_ids}: {e}")
    return summary


# ---------------------------------------------------------------------
# Season stats
# ---------------------------------------------------------------------
def sync_season_stats(season: int = NFL_SEASON) -> dict:
    raw = fetch_season_stats(season)  # empty before the first kickoff of the season
    relevant = [r for r in raw if _relevant(r, _SEASON_ATT_KEYS)]
    available = _ensure_players(relevant)
    rows = [
        n
        for n in (normalize_season(r, season) for r in relevant)
        if n and n["player_id"] in available
    ]
    for batch in chunk(rows, DB_BATCH_SIZE):
        get_db().table("player_season_stats").upsert(batch, on_conflict="player_id,season").execute()
    return {"season": season, "players": len(rows)}


def sync_stats(
    season: int = NFL_SEASON,
    max_games: int = 10,
    backfill: bool = False,
    include_season_stats: bool = True,
) -> dict:
    out = {"ok": True, "game_logs": sync_game_logs(season, max_games, backfill)}
    if include_season_stats:
        out["season_stats"] = sync_season_stats(season)
    return out