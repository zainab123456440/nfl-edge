from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from config import NFL_SEASON
from services import props_queries, queries

router = APIRouter(
    prefix="/props",
    tags=["props"],
)


# Plain `def` endpoints: the Supabase client is sync, so FastAPI runs
# them in its threadpool instead of blocking the event loop.


def _week_game_ids(
    season: int,
    week: int | None,
    game_id: int | None,
) -> list[int] | None:
    """
    Resolve the game IDs for the requested week.

    If a specific game_id is supplied, no week filtering is applied.
    If week is omitted, use the current NFL week.
    """
    if game_id is not None:
        return None

    week = (
        week
        if week is not None
        else queries.current_week(season)
    )

    return (
        props_queries.resolve_game_ids(season, week)
        if week is not None
        else None
    )


# ---------------------------------------------------------------------
# Markets
# ---------------------------------------------------------------------

@router.get("/markets")
def list_markets():
    """
    Return available player-prop markets.

    This is shared NFL data and does not require a user ID.
    """
    return props_queries.list_markets()


# ---------------------------------------------------------------------
# Props board
# ---------------------------------------------------------------------

@router.get("/board")
def props_board(
    season: int = NFL_SEASON,
    week: int | None = None,
    game_id: int | None = None,
    market: str | None = None,
    team_id: int | None = None,
    position: str | None = None,
    search: str | None = None,
    book: str | None = None,
):
    """
    Return one row per player + market with sportsbook data.

    Props are shared application data, not user-owned data.
    """
    data = props_queries.build_board(
        game_id=game_id,
        market=market,
        team_id=team_id,
        position=position,
        search=search,
        game_ids=_week_game_ids(
            season,
            week,
            game_id,
        ),
        book=book,
    )

    return {
        "count": len(data),
        "data": data,
    }


# ---------------------------------------------------------------------
# Flat props list
# ---------------------------------------------------------------------

@router.get("")
def list_props(
    season: int = NFL_SEASON,
    week: int | None = None,
    game_id: int | None = None,
    player_id: int | None = None,
    market: str | None = None,
    team_id: int | None = None,
    position: str | None = None,
    search: str | None = None,
    book: str | None = None,
    sort: Literal["updated", "movement"] = "updated",
    limit: int = Query(
        50,
        ge=1,
        le=200,
    ),
    offset: int = Query(
        0,
        ge=0,
    ),
):
    """
    Return a flat list of props, one row per sportsbook.

    This is shared NFL data and does not require user ownership.
    """
    rows, total = props_queries.list_props(
        game_id=game_id,
        player_id=player_id,
        market=market,
        team_id=team_id,
        position=position,
        search=search,
        game_ids=_week_game_ids(
            season,
            week,
            game_id,
        ),
        book=book,
        sort=sort,
        limit=limit,
        offset=offset,
    )

    return {
        "count": total,
        "data": rows,
    }


# ---------------------------------------------------------------------
# Single prop
# ---------------------------------------------------------------------

@router.get("/{prop_id}")
def get_prop(
    prop_id: int,
):
    """Return a single shared prop."""
    prop = props_queries.get_prop(prop_id)

    if prop is None:
        raise HTTPException(
            status_code=404,
            detail="Prop not found",
        )

    return prop


# ---------------------------------------------------------------------
# Prop history
# ---------------------------------------------------------------------

@router.get("/{prop_id}/history")
def get_prop_history(
    prop_id: int,
    book: str | None = None,
):
    """
    Return line-movement history for a shared prop.
    """
    prop = props_queries.get_prop(prop_id)

    if prop is None:
        raise HTTPException(
            status_code=404,
            detail="Prop not found",
        )

    history = props_queries.get_history(
        prop,
        book=book,
    )

    return {
        "game_id": prop["game_id"],
        "player_id": prop["player_id"],
        "market": prop["market"],
        "points": history,
    }