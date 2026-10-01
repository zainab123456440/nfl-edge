"""Cron endpoints. They write data into Supabase; a scheduler calls them."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from config import (
    DB_BATCH_SIZE,
    NFL_SEASON,
    ODDS_WINDOW_FUTURE_DAYS,
    ODDS_WINDOW_PAST_HOURS,
)
from db import get_db
from security import verify_cron
from services.balldontlie import (
    fetch_games,
    fetch_injuries,
    fetch_odds,
    fetch_teams,
)
from services.normalize import (
    chunk,
    normalize_game,
    normalize_injury,
    normalize_odd,
    normalize_team,
)
from services.players_service import sync_players
from services.prop_service import refresh_props

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cron", tags=["cron"])


def _odds_key(r: dict) -> str:
    return f"{r['game_id']}|{r['book']}|{r['market']}|{r['outcome']}"


def _odds_value(r: dict) -> str:
    line = "null" if r["line"] is None else float(r["line"])
    return f"{line}|{r['price']}"


@router.get("/sync-games")
def sync_games(_=Depends(verify_cron)):
    """Run about hourly. Order matters: teams -> games -> injuries."""
    db = get_db()

    try:
        # 1. Teams
        teams = [normalize_team(t) for t in fetch_teams()]

        db.table("teams").upsert(
            teams,
            on_conflict="id",
        ).execute()

        # 2. Games
        games = [
            g
            for g in (normalize_game(x) for x in fetch_games(NFL_SEASON))
            if g
        ]

        for batch in chunk(games, DB_BATCH_SIZE):
            db.table("games").upsert(
                batch,
                on_conflict="id",
            ).execute()

        # 3. Injuries
        incoming = [
            i
            for i in (normalize_injury(x) for x in fetch_injuries())
            if i
        ]

        latest = (
            db.table("latest_injuries")
            .select(
                "player_id,player_name,position,team_id,status,description"
            )
            .neq("status", "Cleared")
            .execute()
            .data
            or []
        )

        latest_by_id = {
            r["player_id"]: r
            for r in latest
        }

        seen: set[int] = set()
        to_insert: list[dict] = []

        for inj in incoming:
            seen.add(inj["player_id"])
            prev = latest_by_id.get(inj["player_id"])

            if (
                prev is None
                or prev["status"] != inj["status"]
                or (prev.get("description") or None)
                != (inj.get("description") or None)
            ):
                to_insert.append(inj)

        # Player dropped off the feed -> record as Cleared.
        for prev in latest:
            if prev["player_id"] not in seen:
                to_insert.append(
                    {
                        "player_id": prev["player_id"],
                        "player_name": prev["player_name"],
                        "position": prev.get("position"),
                        "team_id": prev["team_id"],
                        "status": "Cleared",
                        "description": None,
                        "reported_at": None,
                    }
                )

        for batch in chunk(to_insert, DB_BATCH_SIZE):
            db.table("injuries").insert(batch).execute()

        return {
            "ok": True,
            "teams": len(teams),
            "games": len(games),
            "injuries_checked": len(incoming),
            "injuries_inserted": len(to_insert),
        }

    except Exception as e:
        logger.exception("sync-games failed")

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.get("/poll-odds")
def poll_odds(_=Depends(verify_cron)):
    """
    Run every 15-30 minutes.

    Stores a new odds snapshot whenever a line or price changes.

    IMPORTANT:
    We no longer restrict bookmakers to a fixed BOOKS list.
    Every bookmaker returned by BALLDONTLIE is accepted.
    """

    db = get_db()

    try:
        # 1. Determine which games currently need odds.
        now = datetime.now(timezone.utc)

        start = (
            now - timedelta(hours=ODDS_WINDOW_PAST_HOURS)
        ).isoformat()

        end = (
            now + timedelta(days=ODDS_WINDOW_FUTURE_DAYS)
        ).isoformat()

        games = (
            db.table("games")
            .select("id,season,week")
            .gte("kickoff_at", start)
            .lte("kickoff_at", end)
            .neq("status", "final")
            .execute()
            .data
            or []
        )

        if not games:
            return {
                "ok": True,
                "note": "No games in window",
                "inserted": 0,
            }

        game_ids = {
            g["id"]
            for g in games
        }

        weeks = {
            (g["season"], g["week"])
            for g in games
            if g.get("week") is not None
        }

        # 2. Fetch odds from BALLDONTLIE.
        incoming: list[dict] = []

        for season, week in weeks:
            odds_response = fetch_odds(season, week)

            for o in odds_response:
                if o["game_id"] not in game_ids:
                    logger.warning(
                        "ODDS GAME ID MISMATCH: odds_game_id=%s",
                        o["game_id"],
                    )
                    continue

                logger.info(
                    "ODDS RECEIVED: game=%s vendor=%s",
                    o["game_id"],
                    o.get("vendor"),
                )

                normalized = normalize_odd(o)

                if normalized:
                    incoming.extend(normalized)

        # 3. Nothing came back after filtering/normalization.
        if not incoming:
            logger.warning(
                "No usable odds received for game_ids=%s",
                list(game_ids),
            )

            return {
                "ok": True,
                "games": len(game_ids),
                "weeks": len(weeks),
                "rows_checked": 0,
                "inserted": 0,
                "note": "No usable odds returned",
            }

        # 4. Get the latest stored snapshot.
        latest = (
            db.table("latest_odds")
            .select(
                "game_id,book,market,outcome,line,price"
            )
            .in_("game_id", list(game_ids))
            .limit(5000)
            .execute()
            .data
            or []
        )

        latest_map = {
            _odds_key(r): _odds_value(r)
            for r in latest
        }

        # 5. Only save changed odds.
        changed = [
            r
            for r in incoming
            if latest_map.get(_odds_key(r))
            != _odds_value(r)
        ]

        # 6. Insert snapshots.
        for batch in chunk(changed, DB_BATCH_SIZE):
            db.table("odds_snapshots").insert(batch).execute()

        # 7. Useful diagnostic information.
        books_received = sorted(
            {
                r.get("book")
                for r in incoming
                if r.get("book")
            }
        )

        return {
            "ok": True,
            "games": len(game_ids),
            "weeks": len(weeks),
            "rows_checked": len(incoming),
            "changed_rows": len(changed),
            "inserted": len(changed),
            "books_received": books_received,
        }

    except Exception as e:
        logger.exception("poll-odds failed")

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@router.api_route("/refresh-props", methods=["GET", "POST"])
async def cron_refresh_props(_=Depends(verify_cron)):
    """Refresh player props (Odds API -> props_current / props_history)."""
    return await refresh_props()


@router.get("/sync-players")
def cron_sync_players(_=Depends(verify_cron)):
    """Run once before the first props refresh, then daily. Needs teams synced first."""
    try:
        return sync_players()

    except Exception as e:
        logger.exception("sync-players failed")

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )