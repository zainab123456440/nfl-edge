"""Props ingest: BALLDONTLIE live NFL player props -> Supabase.

Per run:
  1. Load reference data (active markets, bookmakers, known player ids).
  2. Pick games in the odds window (same config as /poll-odds).
  3. Per game: GET /odds/player_props (one call, not paginated).
  4. Keep one row per player + market + book (the main line).
  5. Diff against props_current; upsert only changes; append props_history.
     New rows get their opening line from /odds/player_props/opening when available.

BALLDONTLIE keeps no history, so every change we see is stored in props_history.
Player ids are BALLDONTLIE ids and equal players.id. Unknown players are fetched
on the fly, so no name matching is needed.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from config import DB_BATCH_SIZE, ODDS_WINDOW_FUTURE_DAYS, ODDS_WINDOW_PAST_HOURS
from db import get_db
from services.balldontlie import fetch_opening_player_props, fetch_player_props
from services.normalize import chunk
from services.players_service import ensure_players

logger = logging.getLogger(__name__)

PAGE = 1000
MILESTONE_PREFIXES = ("anytime_td", "first_td")


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _select_all(table: str, columns: str = "*", **eq_filters) -> list:
    """Paginate past PostgREST's 1000-row default limit."""
    rows, start = [], 0
    while True:
        q = get_db().table(table).select(columns)
        for col, val in eq_filters.items():
            q = q.eq(col, val)
        batch = q.range(start, start + PAGE - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < PAGE:
            return rows
        start += PAGE


def _same(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return float(a) == float(b)


def _implied(odds):
    if odds is None:
        return None
    return 100 / (odds + 100) if odds > 0 else -odds / (-odds + 100)


def _load_reference() -> dict:
    return {
        "markets": {
            m["key"]
            for m in _select_all("prop_markets", "key,is_active")
            if m["is_active"]
        },
        "bookmakers": {
            b["key"]: b["id"]
            for b in _select_all("bookmakers", "id,key,is_active")
            if b["is_active"]
        },
        "players": {p["id"] for p in _select_all("players", "id")},
    }


# ---------------------------------------------------------------------
# Parse: raw BDL props -> one row per (player, market, book)
# ---------------------------------------------------------------------
def parse_props(props: list, ref: dict, unknown_vendors: set) -> list:
    """Keeps the main line per key: over/under rows win, and among several
    lines the most balanced one (closest to even money on both sides)."""
    best: dict = {}
    for p in props:
        market = p.get("prop_type")
        if market not in ref["markets"]:
            continue
        book_id = ref["bookmakers"].get(p.get("vendor"))
        if book_id is None:
            unknown_vendors.add(p.get("vendor"))
            continue

        m = p.get("market") or {}
        try:
            line = float(p["line_value"]) if p.get("line_value") not in (None, "") else None
        except (TypeError, ValueError):
            line = None

        if m.get("type") == "over_under":
            over, under, rank = m.get("over_odds"), m.get("under_odds"), 0
        elif m.get("type") == "milestone" and market.startswith(MILESTONE_PREFIXES):
            over, under, rank = m.get("odds"), None, 1  # "yes" price stored as over_odds
        else:
            continue  # alt milestone ladders (e.g. 100+ yards) are ignored

        po, pu = _implied(over), _implied(under)
        balance = abs(po - pu) if po is not None and pu is not None else 0.0
        score = (rank, balance)

        key = (p["player_id"], market, book_id)
        cur = best.get(key)
        if cur is None or score < cur["_score"]:
            best[key] = {
                "player_id": p["player_id"],
                "market": market,
                "bookmaker_id": book_id,
                "line": line,
                "over_odds": over,
                "under_odds": under,
                "_score": score,
            }

    rows = list(best.values())
    for r in rows:
        r.pop("_score")
    return rows


def _opening_map(game_id: int, ref: dict) -> dict:
    try:
        props = fetch_opening_player_props(game_id)
    except Exception as e:  # opening data is a bonus; never fail the run over it
        logger.warning("opening props unavailable for game %s: %s", game_id, e)
        return {}
    rows = parse_props(props, ref, set())
    return {(r["player_id"], r["market"], r["bookmaker_id"]): r for r in rows}


# ---------------------------------------------------------------------
# Persist: diff against props_current, upsert changes, append history
# ---------------------------------------------------------------------
def persist_game(game_id: int, rows: list, ref: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    existing = {
        (r["player_id"], r["market"], r["bookmaker_id"]): r
        for r in _select_all("props_current", game_id=game_id)
    }
    has_new = any((r["player_id"], r["market"], r["bookmaker_id"]) not in existing for r in rows)
    opening = _opening_map(game_id, ref) if has_new else {}

    upserts, history = [], []
    stats = {"inserted": 0, "updated": 0, "unchanged": 0}

    for r in rows:
        k = (r["player_id"], r["market"], r["bookmaker_id"])
        old = existing.get(k)

        if old is None:
            o = opening.get(k) or r
            opening_vals = (o["line"], o["over_odds"], o["under_odds"])
            stats["inserted"] += 1
        elif not (
            _same(old["line"], r["line"])
            and _same(old["over_odds"], r["over_odds"])
            and _same(old["under_odds"], r["under_odds"])
        ):
            opening_vals = (
                old["opening_line"] if old.get("opening_line") is not None else old["line"],
                old["opening_over_odds"] if old.get("opening_over_odds") is not None else old["over_odds"],
                old["opening_under_odds"] if old.get("opening_under_odds") is not None else old["under_odds"],
            )
            stats["updated"] += 1
        else:
            stats["unchanged"] += 1
            continue

        upserts.append({
            "game_id": game_id, **r,
            "opening_line": opening_vals[0],
            "opening_over_odds": opening_vals[1],
            "opening_under_odds": opening_vals[2],
            "line_changed_at": now,
            "updated_at": now,
        })
        history.append({"game_id": game_id, **r, "recorded_at": now})

    for batch in chunk(upserts, DB_BATCH_SIZE):
        get_db().table("props_current").upsert(
            batch, on_conflict="game_id,player_id,market,bookmaker_id"
        ).execute()
    for batch in chunk(history, DB_BATCH_SIZE):
        get_db().table("props_history").insert(batch).execute()
    return stats


# ---------------------------------------------------------------------
# Public entry point (called from routes/cron.py)
# ---------------------------------------------------------------------
def _refresh_sync(max_games: int | None = None) -> dict:
    ref = _load_reference()
    if not ref["markets"] or not ref["bookmakers"]:
        return {"ok": False, "error": "prop_markets or bookmakers is empty; run props_bdl_migration.sql"}

    now = datetime.now(timezone.utc)
    games = (
        get_db().table("games")
        .select("id,kickoff_at")
        .gte("kickoff_at", (now - timedelta(hours=ODDS_WINDOW_PAST_HOURS)).isoformat())
        .lte("kickoff_at", (now + timedelta(days=ODDS_WINDOW_FUTURE_DAYS)).isoformat())
        .neq("status", "final")
        .order("kickoff_at")
        .limit(200)
        .execute()
        .data
        or []
    )
    if max_games:
        games = games[:max_games]
    if not games:
        return {"ok": True, "note": "No games in window", "inserted": 0}

    summary = {
        "ok": True, "games": len(games), "games_with_props": 0,
        "inserted": 0, "updated": 0, "unchanged": 0,
        "skipped_unknown_players": 0, "unknown_vendors": [], "errors": [],
    }
    unknown_vendors: set = set()

    for g in games:
        try:
            props = fetch_player_props(g["id"])
            if not props:
                continue
            rows = parse_props(props, ref, unknown_vendors)

            missing = {r["player_id"] for r in rows} - ref["players"]
            if missing:
                ref["players"] |= ensure_players(missing)
            kept = [r for r in rows if r["player_id"] in ref["players"]]
            summary["skipped_unknown_players"] += len(rows) - len(kept)

            stats = persist_game(g["id"], kept, ref)
            summary["games_with_props"] += 1
            for k in ("inserted", "updated", "unchanged"):
                summary[k] += stats[k]
        except Exception as e:  # one bad game must not stop the rest
            logger.exception("props refresh failed for game %s", g["id"])
            summary["errors"].append(f"game {g['id']}: {e}")

    summary["unknown_vendors"] = sorted(v for v in unknown_vendors if v)
    return summary


async def refresh_props(max_games: int | None = None) -> dict:
    """Async wrapper so the existing `await refresh_props()` in cron.py keeps working."""
    return await asyncio.to_thread(_refresh_sync, max_games)