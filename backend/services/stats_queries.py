"""Hit rates and recent form for the Props page.

Hit rate = how often the player's stat would have gone OVER today's line in
past games ("would this line have hit?"). BALLDONTLIE keeps no prop history,
so past lines are not available.
"""
from datetime import date, timedelta
from typing import Optional

from config import NFL_SEASON
from db import get_db

PAGE = 1000
BOARD_LOG_DAYS = 400
BOARD_PLAYER_CAP = 500
BOARD_PAGE_CAP = 10

# stat_column values allowed to be interpolated into a select string
LOG_COLUMNS = {
    "pass_yds", "pass_td", "pass_att", "pass_cmp", "pass_int",
    "rush_yds", "rush_att", "rush_long", "receptions", "rec_yds", "rec_long",
    "rush_rec_yds", "total_td", "fg_made", "kicking_points",
}


# ---------------------------------------------------------------- helpers

def market_stat_column(market: str) -> Optional[str]:
    rows = (
        get_db().table("prop_markets").select("stat_column").eq("key", market).limit(1).execute().data
        or []
    )
    col = rows[0]["stat_column"] if rows else None
    return col if col in LOG_COLUMNS else None


def _market_columns() -> dict[str, str]:
    rows = get_db().table("prop_markets").select("key,stat_column").execute().data or []
    return {r["key"]: r["stat_column"] for r in rows if r["stat_column"] in LOG_COLUMNS}


def _summarize(values: list[float], line: Optional[float]) -> dict:
    n = len(values)
    if n == 0:
        return {"games": 0, "over": 0, "under": 0, "push": 0, "over_pct": None, "avg": None}
    avg = round(sum(values) / n, 2)
    if line is None:
        return {"games": n, "over": None, "under": None, "push": None, "over_pct": None, "avg": avg}
    over = sum(1 for v in values if v > line)
    under = sum(1 for v in values if v < line)
    return {
        "games": n,
        "over": over,
        "under": under,
        "push": n - over - under,
        "over_pct": round(100 * over / n, 1),
        "avg": avg,
    }


def _player_logs(player_id: int, col: str, limit: int = 300) -> list[dict]:
    """Newest first. Rows without a value for the stat are dropped."""
    rows = (
        get_db()
        .table("player_game_logs")
        .select(f"game_id,game_date,week,season,team_id,opponent_team_id,is_home,{col}")
        .eq("player_id", player_id)
        .order("game_date", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )
    return [r for r in rows if r.get(col) is not None]


def _team_abbrs(ids: set) -> dict[int, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    rows = get_db().table("teams").select("id,abbreviation").in_("id", list(ids)).execute().data or []
    return {r["id"]: r["abbreviation"] for r in rows}


def _opponent_for(game_id: Optional[int], player_id: int) -> Optional[int]:
    if game_id is None:
        return None
    g = get_db().table("games").select("home_team_id,away_team_id").eq("id", game_id).limit(1).execute().data
    p = get_db().table("players").select("team_id").eq("id", player_id).limit(1).execute().data
    if not g or not p or p[0]["team_id"] is None:
        return None
    team = p[0]["team_id"]
    if team == g[0]["home_team_id"]:
        return g[0]["away_team_id"]
    if team == g[0]["away_team_id"]:
        return g[0]["home_team_id"]
    return None


# ---------------------------------------------------------------- public

def hit_rate(
    player_id: int,
    market: str,
    line: Optional[float],
    game_id: Optional[int] = None,
    season: int = NFL_SEASON,
) -> dict:
    col = market_stat_column(market)
    if col is None:
        return {"supported": False, "market": market, "reason": "No stat to compare for this market"}

    rows = _player_logs(player_id, col)
    vals = lambda rs: [float(r[col]) for r in rs]  # noqa: E731

    windows = {
        "last_5": _summarize(vals(rows[:5]), line),
        "last_10": _summarize(vals(rows[:10]), line),
        "season": _summarize(vals([r for r in rows if r["season"] == season]), line),
        "home": _summarize(vals([r for r in rows[:20] if r["is_home"] is True]), line),
        "away": _summarize(vals([r for r in rows[:20] if r["is_home"] is False]), line),
        "all": _summarize(vals(rows), line),
    }

    opp_id = _opponent_for(game_id, player_id)
    vs = None
    if opp_id is not None:
        vs = _summarize(vals([r for r in rows if r["opponent_team_id"] == opp_id]), line)
        vs["opponent"] = _team_abbrs({opp_id}).get(opp_id)
    windows["vs_opponent"] = vs

    return {
        "supported": True,
        "player_id": player_id,
        "market": market,
        "stat_column": col,
        "line": line,
        "games_available": len(rows),
        "windows": windows,
    }


def recent_games(player_id: int, market: str, line: Optional[float], limit: int = 10) -> dict:
    """Last N games, oldest first (ready for a left-to-right bar chart)."""
    col = market_stat_column(market)
    if col is None:
        return {"supported": False, "market": market, "games": []}

    rows = _player_logs(player_id, col)[:limit]
    abbrs = _team_abbrs({r["opponent_team_id"] for r in rows})

    games = []
    for r in reversed(rows):
        v = float(r[col])
        result = None
        if line is not None:
            result = "over" if v > line else "under" if v < line else "push"
        games.append({
            "game_id": r["game_id"],
            "date": r["game_date"],
            "week": r["week"],
            "season": r["season"],
            "opponent": abbrs.get(r["opponent_team_id"]),
            "is_home": r["is_home"],
            "value": v,
            "result": result,
        })
    return {
        "supported": True,
        "player_id": player_id,
        "market": market,
        "stat_column": col,
        "line": line,
        "games": games,
    }


def attach_hit_rates(board: list[dict], n: int = 10) -> list[dict]:
    """Adds `hit_rate` (last n games vs the consensus line) to each board row.

    One paged query for all players on the board, instead of one per row.
    Never raises: on any problem the rows just get hit_rate = None.
    """
    for g in board:
        g["hit_rate"] = None
    try:
        cols = _market_columns()
        player_ids = list({g["player_id"] for g in board})[:BOARD_PLAYER_CAP]
        needed = sorted({cols[g["market"]] for g in board if g["market"] in cols})
        if not player_ids or not needed:
            return board

        since = (date.today() - timedelta(days=BOARD_LOG_DAYS)).isoformat()
        by_player: dict[int, list[dict]] = {}
        start = 0
        for _ in range(BOARD_PAGE_CAP):
            batch = (
                get_db()
                .table("player_game_logs")
                .select("player_id,game_date," + ",".join(needed))
                .in_("player_id", player_ids)
                .gte("game_date", since)
                .order("game_date", desc=True)
                .range(start, start + PAGE - 1)
                .execute()
                .data
                or []
            )
            for r in batch:
                by_player.setdefault(r["player_id"], []).append(r)
            if len(batch) < PAGE:
                break
            start += PAGE

        for g in board:
            col = cols.get(g["market"])
            if not col:
                continue
            logs = [r for r in by_player.get(g["player_id"], []) if r.get(col) is not None][:n]
            s = _summarize([float(r[col]) for r in logs], g.get("consensus_line"))
            s["window"] = n
            g["hit_rate"] = s if s["games"] else None
    except Exception as e:
        print(f"hit-rate join skipped: {e}")
    return board