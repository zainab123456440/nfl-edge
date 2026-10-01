"""Read-side queries for the props page. Kept separate from queries.py."""
from statistics import median
from typing import Optional

from db import get_db

PROP_SELECT = (
    "id,game_id,player_id,market,bookmaker_id,line,over_odds,under_odds,"
    "opening_line,line_movement,updated_at,"
    "players!inner(name,position,team_id),bookmakers!inner(key,name)"
)
PAGE = 1000
BOARD_CAP = 5000


def _flatten(r: dict) -> dict:
    p = r.pop("players", None) or {}
    b = r.pop("bookmakers", None) or {}
    r["player_name"] = p.get("name")
    r["position"] = p.get("position")
    r["team_id"] = p.get("team_id")
    r["bookmaker"] = b.get("name")
    r["bookmaker_key"] = b.get("key")
    return r


def _base_query(game_id, player_id, market, bookmaker_id, team_id, position, search,
                game_ids=None, book=None):
    q = get_db().table("props_current").select(PROP_SELECT, count="exact")
    if game_id is not None:
        q = q.eq("game_id", game_id)
    if player_id is not None:
        q = q.eq("player_id", player_id)
    if market:
        q = q.eq("market", market)
    if bookmaker_id is not None:
        q = q.eq("bookmaker_id", bookmaker_id)
    if team_id is not None:
        q = q.eq("players.team_id", team_id)
    if position:
        q = q.eq("players.position", position.upper())
    if search:
        q = q.ilike("players.name", f"%{search}%")
    if game_ids is not None:
        q = q.in_("game_id", game_ids or [-1])  # empty week -> no rows
    if book:
        q = q.eq("bookmakers.key", book)
    return q


def resolve_game_ids(season: Optional[int], week: Optional[int]) -> list:
    """Game ids for a season/week. Assumes games has season + week columns."""
    q = get_db().table("games").select("id")
    if season is not None:
        q = q.eq("season", season)
    if week is not None:
        q = q.eq("week", week)
    return [g["id"] for g in q.limit(1000).execute().data or []]


def attach_injuries(rows: list) -> list:
    """Adds injury_status from latest_injuries (player_id is the BDL id = players.id)."""
    ids = list({r["player_id"] for r in rows})
    status: dict = {}
    if ids:
        try:
            inj = (
                get_db()
                .table("latest_injuries")
                .select("player_id,status")
                .in_("player_id", ids)
                .neq("status", "Cleared")
                .limit(2000)
                .execute()
                .data
                or []
            )
            status = {i["player_id"]: i["status"] for i in inj}
        except Exception as e:  # never break the props page over injuries
            print(f"injury join skipped: {e}")
    for r in rows:
        r["injury_status"] = status.get(r["player_id"])
    return rows


def list_props(
    game_id: Optional[int] = None,
    player_id: Optional[int] = None,
    market: Optional[str] = None,
    bookmaker_id: Optional[int] = None,
    team_id: Optional[int] = None,
    position: Optional[str] = None,
    search: Optional[str] = None,
    game_ids: Optional[list] = None,
    book: Optional[str] = None,
    sort: str = "updated",
    limit: int = 50,
    offset: int = 0,
):
    q = _base_query(game_id, player_id, market, bookmaker_id, team_id, position, search, game_ids, book)
    if sort == "movement":
        q = q.order("line_movement", desc=True, nullsfirst=False)
    else:
        q = q.order("updated_at", desc=True)
    res = q.range(offset, offset + limit - 1).execute()
    rows = [_flatten(r) for r in res.data or []]
    return attach_injuries(rows), res.count or 0


def get_prop(prop_id: int) -> Optional[dict]:
    res = (
        get_db().table("props_current")
        .select(PROP_SELECT)
        .eq("id", prop_id)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    return attach_injuries([_flatten(res.data[0])])[0]


def get_history(prop: dict, book: Optional[str] = None) -> list:
    q = (
        get_db().table("props_history")
        .select("bookmaker_id,line,over_odds,under_odds,recorded_at,bookmakers!inner(key,name)")
        .eq("game_id", prop["game_id"])
        .eq("player_id", prop["player_id"])
        .eq("market", prop["market"])
    )
    if book:
        q = q.eq("bookmakers.key", book)
    rows = q.order("recorded_at", desc=False).limit(2000).execute().data or []
    for r in rows:
        b = r.pop("bookmakers", None) or {}
        r["bookmaker"] = b.get("name")
    return rows


def list_markets() -> list:
    return (
        get_db().table("prop_markets")
        .select("key,label,position_group")
        .eq("is_active", True)
        .order("sort_order")
        .execute()
        .data
        or []
    )


def build_board(
    game_id=None, player_id=None, market=None, bookmaker_id=None,
    team_id=None, position=None, search=None, game_ids=None, book=None,
) -> list:
    """One row per player+market with every book side by side."""
    rows, start = [], 0
    while start < BOARD_CAP:
        q = _base_query(game_id, player_id, market, bookmaker_id, team_id, position, search, game_ids, book)
        batch = q.order("id").range(start, start + PAGE - 1).execute().data or []
        rows.extend(_flatten(r) for r in batch)
        if len(batch) < PAGE:
            break
        start += PAGE

    attach_injuries(rows)
    groups: dict = {}
    for r in rows:
        key = (r["game_id"], r["player_id"], r["market"])
        g = groups.setdefault(key, {
            "game_id": r["game_id"], "player_id": r["player_id"],
            "player_name": r["player_name"], "position": r["position"],
            "team_id": r["team_id"], "market": r["market"],
            "injury_status": r["injury_status"], "books": [],
        })
        g["books"].append({
            "bookmaker_id": r["bookmaker_id"], "bookmaker": r["bookmaker"],
            "line": r["line"], "over_odds": r["over_odds"], "under_odds": r["under_odds"],
            "opening_line": r["opening_line"], "line_movement": r["line_movement"],
            "updated_at": r["updated_at"],
        })

    board = []
    for g in groups.values():
        lines = [b["line"] for b in g["books"] if b["line"] is not None]
        overs = [b for b in g["books"] if b["over_odds"] is not None]
        unders = [b for b in g["books"] if b["under_odds"] is not None]
        moves = [b["line_movement"] for b in g["books"] if b["line_movement"] is not None]
        g["consensus_line"] = median(lines) if lines else None
        g["avg_movement"] = round(sum(moves) / len(moves), 2) if moves else None
        best_o = max(overs, key=lambda b: b["over_odds"], default=None)  # higher American = better
        best_u = max(unders, key=lambda b: b["under_odds"], default=None)
        g["best_over"] = {"bookmaker": best_o["bookmaker"], "odds": best_o["over_odds"]} if best_o else None
        g["best_under"] = {"bookmaker": best_u["bookmaker"], "odds": best_u["under_odds"]} if best_u else None
        board.append(g)

    board.sort(key=lambda g: abs(g["avg_movement"] or 0), reverse=True)
    return board