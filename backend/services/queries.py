"""Read logic for the Games page.

Kept separate from the routes on purpose: the API endpoints AND the AI assistant's
tools (later) can call these same functions, so numbers always match.
"""
from datetime import datetime, timezone

from config import BOOKS, NFL_SEASON
from db import get_db

DEFAULT_OUTCOME = {"spreads": "home", "totals": "over", "h2h": "home"}
VALID_OUTCOMES = {
    "spreads": {"home", "away"},
    "totals": {"over", "under"},
    "h2h": {"home", "away"},
}
# lower number = more serious
INJURY_ORDER = {"out": 0, "injured reserve": 0, "ir": 0, "doubtful": 1, "questionable": 2}


# ---------------------------------------------------------------- helpers

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _teams_map() -> dict[int, dict]:
    rows = (
        get_db()
        .table("teams")
        .select("id,name,abbreviation,city,conference,division")
        .execute()
        .data
        or []
    )
    return {t["id"]: t for t in rows}


def group_odds(rows: list[dict]) -> dict[str, dict]:
    """Long rows (one per outcome) -> one object per sportsbook:

    {
      "draftkings": {
        "spread":    {"home": {"line": -3.5, "price": -110}, "away": {"line": 3.5, "price": -110}},
        "total":     {"line": 47.5, "over": -110, "under": -110},
        "moneyline": {"home": -180, "away": 150},
        "updated_at": "..."
      }
    }
    """
    books: dict[str, dict] = {}
    for r in rows:
        b = books.setdefault(
            r["book"], {"spread": {}, "total": {}, "moneyline": {}, "updated_at": None}
        )
        market, outcome = r["market"], r["outcome"]
        if market == "spreads":
            b["spread"][outcome] = {"line": r["line"], "price": r["price"]}
        elif market == "totals":
            b["total"]["line"] = r["line"]
            b["total"][outcome] = r["price"]
        elif market == "h2h":
            b["moneyline"][outcome] = r["price"]

        ts = r.get("captured_at")
        if ts and (b["updated_at"] is None or ts > b["updated_at"]):
            b["updated_at"] = ts
    return books


def _avg(values) -> float | None:
    vals = [float(v) for v in values if v is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def _movement(current: dict[str, dict], opening: dict[str, dict]) -> dict:
    """Average line across books, now vs open. change > 0 means the number went up."""

    def build(cur: float | None, opn: float | None) -> dict:
        change = round(cur - opn, 2) if cur is not None and opn is not None else None
        return {"open": opn, "current": cur, "change": change}

    cur_spread = _avg(b["spread"].get("home", {}).get("line") for b in current.values())
    opn_spread = _avg(b["spread"].get("home", {}).get("line") for b in opening.values())
    cur_total = _avg(b["total"].get("line") for b in current.values())
    opn_total = _avg(b["total"].get("line") for b in opening.values())
    return {
        "spread_home": build(cur_spread, opn_spread),
        "total": build(cur_total, opn_total),
    }


def _game_out(g: dict, teams: dict[int, dict]) -> dict:
    return {
        "id": g["id"],
        "season": g["season"],
        "week": g["week"],
        "kickoff_at": g["kickoff_at"],
        "status": g["status"],
        "home_score": g["home_score"],
        "away_score": g["away_score"],
        "venue": g["venue"],
        "home_team": teams.get(g["home_team_id"]),
        "away_team": teams.get(g["away_team_id"]),
    }


def _fetch_odds(view: str, game_ids: list[int], book: str | None) -> dict[int, dict[str, dict]]:
    """Read latest_odds or opening_odds for many games -> {game_id: {book: {...}}}"""
    if not game_ids:
        return {}
    q = (
        get_db()
        .table(view)
        .select("game_id,book,market,outcome,line,price,captured_at")
        .in_("game_id", game_ids)
        .limit(5000)
    )
    if book:
        q = q.eq("book", book)
    rows = q.execute().data or []

    by_game: dict[int, list[dict]] = {}
    for r in rows:
        by_game.setdefault(r["game_id"], []).append(r)
    return {gid: group_odds(rs) for gid, rs in by_game.items()}


# ---------------------------------------------------------------- week logic

def current_week(season: int) -> int | None:
    """Week of the next unfinished game; falls back to the last week of the season."""
    db = get_db()
    upcoming = (
        db.table("games")
        .select("week")
        .eq("season", season)
        .neq("status", "final")
        .order("kickoff_at")
        .limit(10)
        .execute()
        .data
        or []
    )
    for r in upcoming:
        if r["week"] is not None:
            return r["week"]

    last = (
        db.table("games")
        .select("week")
        .eq("season", season)
        .order("week", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    return last[0]["week"] if last else None


def available_weeks(season: int) -> list[int]:
    rows = get_db().table("games").select("week").eq("season", season).execute().data or []
    return sorted({r["week"] for r in rows if r["week"] is not None})


# ---------------------------------------------------------------- public queries

def list_games(
    season: int = NFL_SEASON,
    week: int | None = None,
    team: str | None = None,
    book: str | None = None,
) -> dict:
    week = week if week is not None else current_week(season)
    teams = _teams_map()

    games: list[dict] = []
    if week is not None:
        games = (
            get_db()
            .table("games")
            .select("*")
            .eq("season", season)
            .eq("week", week)
            .order("kickoff_at")
            .execute()
            .data
            or []
        )

    if team:
        needle = team.strip().lower()
        games = [
            g
            for g in games
            if any(
                needle in f"{t['name']} {t['abbreviation']}".lower()
                for t in (teams.get(g["home_team_id"]), teams.get(g["away_team_id"]))
                if t
            )
        ]

    ids = [g["id"] for g in games]
    current = _fetch_odds("latest_odds", ids, book)
    opening = _fetch_odds("opening_odds", ids, book)

    out = []
    for g in games:
        cur = current.get(g["id"], {})
        opn = opening.get(g["id"], {})
        item = _game_out(g, teams)
        item["odds"] = cur
        item["movement"] = _movement(cur, opn)
        out.append(item)

    return {
        "season": season,
        "week": week,
        "weeks": available_weeks(season),
        "books": BOOKS,
        "games": out,
    }


def get_game_detail(game_id: int) -> dict | None:
    db = get_db()
    rows = db.table("games").select("*").eq("id", game_id).limit(1).execute().data or []
    if not rows:
        return None
    game = rows[0]
    teams = _teams_map()

    current = _fetch_odds("latest_odds", [game_id], None).get(game_id, {})
    opening = _fetch_odds("opening_odds", [game_id], None).get(game_id, {})

    injuries = (
        db.table("latest_injuries")
        .select("player_id,player_name,position,team_id,status,description,reported_at,captured_at")
        .in_("team_id", [game["home_team_id"], game["away_team_id"]])
        .neq("status", "Cleared")
        .execute()
        .data
        or []
    )
    injuries.sort(key=lambda i: (INJURY_ORDER.get((i["status"] or "").lower(), 3), i["player_name"]))

    out = _game_out(game, teams)
    out["odds"] = current
    out["opening"] = opening
    out["movement"] = _movement(current, opening)
    out["injuries"] = injuries
    return out


def get_line_history(
    game_id: int,
    market: str = "spreads",
    outcome: str | None = None,
    book: str | None = None,
) -> dict | None:
    """Time series for the line movement chart, one series per sportsbook.

    Snapshots are only stored when a line CHANGES, so we add one final point at
    'now' (marked synthetic) to extend each line to the present. Finished games
    are not extended.
    """
    db = get_db()
    game = db.table("games").select("id,status").eq("id", game_id).limit(1).execute().data or []
    if not game:
        return None

    outcome = outcome or DEFAULT_OUTCOME[market]

    q = (
        db.table("odds_snapshots")
        .select("book,line,price,captured_at")
        .eq("game_id", game_id)
        .eq("market", market)
        .eq("outcome", outcome)
        .order("captured_at")
        .limit(5000)
    )
    if book:
        q = q.eq("book", book)
    rows = q.execute().data or []

    series: dict[str, list[dict]] = {}
    for r in rows:
        series.setdefault(r["book"], []).append(
            {"t": r["captured_at"], "line": r["line"], "price": r["price"]}
        )

    if game[0]["status"] != "final":
        now = _now_iso()
        for points in series.values():
            points.append({**points[-1], "t": now, "synthetic": True})

    return {"game_id": game_id, "market": market, "outcome": outcome, "series": series}