"""
services/assistant_tools.py

The tools the AI model can call, and the safety rules around them.

Safety rules (enforced here in code, never left to the model):
  * Only tables listed in TABLES can be read, and only the listed columns.
  * Read-only: there is no insert / update / delete tool for sports or user data.
  * "user" tables are read with the USER-SCOPED client (row-level security) AND we
    add an explicit owner filter, so a user can only ever see their own rows.
  * "shared" tables hold public sports data (no per-user rows). They are read with
    the service client because RLS on those tables may not allow the anon role.
  * user_id always comes from the verified login token, never from model arguments.
  * Big tables require a filter, and every result is capped (ASSISTANT_MAX_ROWS).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from config.settings import settings
from config.supabase_client import supabase as _service_client
from services import assistant_files as files

log = logging.getLogger("assistant.tools")

MAX_TOOL_CHARS = 24000   # a single tool result sent back to the model
AGG_ROW_CAP = 5000       # rows scanned for sum / avg / min / max / group-by
SORT_ROW_CAP = 2000      # rows scanned when sorting by a computed column


class ToolError(Exception):
    """A problem the model can understand and fix (bad column, missing filter, ...)."""


@dataclass
class ToolContext:
    user_client: Any                      # Supabase client acting as the logged-in user
    user_id: str                          # from the verified token
    conversation_id: str | None = None
    generated_files: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# What the assistant may read.
# scope "shared": public sports data.  scope "user": rows owned by the caller.
# ---------------------------------------------------------------------------
TABLES: dict[str, dict[str, Any]] = {
    "players": {
        "scope": "shared",
        "columns": ["id", "name", "first_name", "last_name", "position", "team_id",
                    "jersey_number", "is_active"],
        "about": "NFL players. 'id' is what player_id means in other tables.",
    },
    "teams": {
        "scope": "shared",
        "columns": ["id", "name", "city", "abbreviation", "conference", "division"],
        "about": "NFL teams. 'id' is what team_id / home_team_id / away_team_id mean.",
    },
    "games": {
        "scope": "shared",
        "columns": ["id", "season", "week", "home_team_id", "away_team_id", "kickoff_at",
                    "status", "home_score", "away_score", "venue"],
        "about": ("Schedule and results. Scores are null until a game is played. "
                  "Computed columns: total_points (home+away) and margin (absolute "
                  "score difference)."),
    },
    "latest_injuries": {
        "scope": "shared",
        "columns": ["id", "player_id", "player_name", "position", "team_id", "status",
                    "description", "reported_at", "captured_at"],
        "about": "CURRENT injury report, one row per injured player. Use for 'who is injured now'.",
    },
    "injuries": {
        "scope": "shared",
        "columns": ["id", "player_id", "player_name", "position", "team_id", "status",
                    "description", "reported_at", "captured_at"],
        "about": "Injury report HISTORY (many snapshots per player over time).",
    },
    "props_current": {
        "scope": "shared",
        "columns": ["id", "game_id", "player_id", "market", "bookmaker_id", "line",
                    "over_odds", "under_odds", "updated_at", "opening_line",
                    "opening_over_odds", "opening_under_odds", "line_changed_at",
                    "line_movement"],
        "about": ("Current player prop lines per bookmaker. Odds are American format. "
                  "line_movement = current line minus opening line."),
    },
    "props_history": {
        "scope": "shared",
        "require_filter": True,
        "columns": ["id", "game_id", "player_id", "market", "bookmaker_id", "line",
                    "over_odds", "under_odds", "recorded_at"],
        "about": "Prop line history over time. Large table.",
    },
    "prop_markets": {
        "scope": "shared",
        "columns": ["key", "label", "stat_column", "position_group", "is_active",
                    "market_type"],
        "about": "Prop market definitions. 'key' matches the 'market' column in props tables.",
    },
    "bookmakers": {
        "scope": "shared",
        "columns": ["id", "key", "name", "is_active"],
        "about": "Sportsbooks. 'id' is what bookmaker_id means.",
    },
    "latest_odds": {
        "scope": "shared",
        "columns": ["game_id", "book", "market", "outcome", "line", "price", "captured_at"],
        "about": "Current game odds (spread / total / moneyline) per book. price = American odds.",
    },
    "opening_odds": {
        "scope": "shared",
        "columns": ["game_id", "book", "market", "outcome", "line", "price", "captured_at"],
        "about": "Opening game odds per book.",
    },
    "odds_snapshots": {
        "scope": "shared",
        "require_filter": True,
        "columns": ["id", "game_id", "book", "market", "outcome", "line", "price",
                    "captured_at"],
        "about": "Game odds history over time. Very large table.",
    },
    # ---- the signed-in user's own rows ----
    "alerts": {
        "scope": "user",
        "owner": "user_id",
        "columns": ["id", "player_id", "market", "condition", "target_value", "is_active",
                    "last_triggered_at", "created_at", "game_id", "bookmaker_id"],
        "about": "The user's own prop alerts.",
    },
    "saved_props": {
        "scope": "user",
        "owner": "user_id",
        "columns": ["id", "player_id", "game_id", "market", "line_at_save", "created_at",
                    "side"],
        "about": "Props the user saved. line_at_save is the line when they saved it.",
    },
    "profiles": {
        "scope": "user",
        "owner": "id",
        "columns": ["id", "email", "full_name", "created_at"],
        "about": "The user's own profile.",
    },
}

# Computed columns (not in the database).
VIRTUAL: dict[str, dict[str, str]] = {
    "games": {"total_points": "home_score + away_score", "margin": "abs(home_score - away_score)"},
}

_OPS = ["eq", "neq", "gt", "gte", "lt", "lte", "ilike", "in", "is_null"]


def schema_prompt() -> str:
    """Compact description of the allowed tables, used in the system prompt."""
    lines = []
    for name, spec in TABLES.items():
        cols = ", ".join(spec["columns"] + list(VIRTUAL.get(name, {})))
        tag = "the user's own rows only" if spec["scope"] == "user" else "shared"
        big = "; large table, always filter" if spec.get("require_filter") else ""
        lines.append(f"- {name} [{tag}{big}]: {spec['about']}\n  columns: {cols}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _table(name: Any) -> tuple[str, dict]:
    key = str(name or "").strip()
    spec = TABLES.get(key)
    if not spec:
        raise ToolError(f"Unknown table '{name}'. Allowed tables: {', '.join(TABLES)}.")
    return key, spec


def _db(ctx: ToolContext, spec: dict) -> Any:
    if spec["scope"] == "user":
        return ctx.user_client
    if _service_client is None:
        raise ToolError("The database is not configured.")
    return _service_client


def _int(value: Any, default: int, lo: int, hi: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(lo, min(hi, number))


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _truthy(value: Any) -> bool:
    return value is True or str(value).strip().lower() in ("true", "1", "yes")


def _list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [_scalar(v) for v in value][:100]
    return [p.strip() for p in str(value).split(",") if p.strip()][:100]


def _like(value: Any) -> str:
    text = _scalar(value)
    return text if "%" in text else f"%{text}%"


def _quote(text: str) -> str:
    """Quote a value for PostgREST's or(...) syntax."""
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _clean_filters(name: str, spec: dict, raw: Any) -> list[tuple[str, str, Any]]:
    out: list[tuple[str, str, Any]] = []
    for f in (raw or [])[:8]:
        if not isinstance(f, dict):
            raise ToolError("Each filter must be an object with column, op and value.")
        col, op = f.get("column"), f.get("op")
        if col not in spec["columns"]:
            raise ToolError(
                f"Cannot filter '{name}' by '{col}'. Filterable columns: "
                f"{', '.join(spec['columns'])}."
            )
        if op not in _OPS:
            raise ToolError(f"Unknown filter op '{op}'. Use one of: {', '.join(_OPS)}.")
        out.append((col, op, f.get("value")))
    return out


def _apply_one(query: Any, col: str, op: str, value: Any) -> Any:
    if op == "eq":
        return query.eq(col, _scalar(value))
    if op == "neq":
        return query.neq(col, _scalar(value))
    if op == "gt":
        return query.gt(col, _scalar(value))
    if op == "gte":
        return query.gte(col, _scalar(value))
    if op == "lt":
        return query.lt(col, _scalar(value))
    if op == "lte":
        return query.lte(col, _scalar(value))
    if op == "ilike":
        return query.ilike(col, _like(value))
    if op == "in":
        return query.in_(col, _list(value))
    if op == "is_null":
        return query.is_(col, "null") if _truthy(value) else query.not_.is_(col, "null")
    raise ToolError(f"Unknown filter op '{op}'.")


def _or_clause(col: str, op: str, value: Any) -> str:
    if op == "is_null":
        return f"{col}.is.null" if _truthy(value) else f"{col}.not.is.null"
    if op == "in":
        return f"{col}.in.({','.join(_quote(v) for v in _list(value))})"
    if op == "ilike":
        return f"{col}.ilike.{_quote(_like(value))}"
    return f"{col}.{op}.{_quote(_scalar(value))}"


def _apply_filters(query: Any, ctx: ToolContext, spec: dict, filters: list, match: str) -> Any:
    if spec.get("owner"):  # user tables: always restricted to the caller
        query = query.eq(spec["owner"], ctx.user_id)
    if match == "any" and len(filters) > 1:
        return query.or_(",".join(_or_clause(c, o, v) for c, o, v in filters))
    for col, op, value in filters:
        query = _apply_one(query, col, op, value)
    return query


def _fetch(ctx: ToolContext, name: str, spec: dict, cols: list[str], filters: list,
           match: str, *, order: str | None = None, desc: bool = False,
           limit: int = 20) -> list[dict]:
    query = _db(ctx, spec).table(name).select(",".join(cols))
    query = _apply_filters(query, ctx, spec, filters, match)
    if order:
        query = query.order(order, desc=desc, nullsfirst=False)
    return query.limit(limit).execute().data or []


def _fetch_all(ctx: ToolContext, name: str, spec: dict, cols: list[str], filters: list,
               match: str, cap: int) -> tuple[list[dict], bool]:
    """Page through results (1000 per request) up to `cap` rows."""
    rows: list[dict] = []
    start = 0
    while len(rows) < cap:
        end = min(start + 999, cap - 1)
        query = _db(ctx, spec).table(name).select(",".join(cols))
        query = _apply_filters(query, ctx, spec, filters, match)
        page = query.order(spec["columns"][0]).range(start, end).execute().data or []
        rows.extend(page)
        if len(page) < end - start + 1:
            break
        start = end + 1
    return rows[:cap], len(rows) >= cap


def _virtual_value(name: str, col: str, row: dict) -> Any:
    if name != "games":
        return None
    home, away = row.get("home_score"), row.get("away_score")
    if home is None or away is None:
        return None
    return home + away if col == "total_points" else abs(home - away)


def _add_virtual(name: str, rows: list[dict]) -> None:
    for col in VIRTUAL.get(name, {}):
        for row in rows:
            row[col] = _virtual_value(name, col, row)


# ---------------------------------------------------------------------------
# Readable names: turn ids into team / player / bookmaker / game labels
# ---------------------------------------------------------------------------
_cache: dict[str, tuple[float, Any]] = {}


def _cached(key: str, loader: Callable[[], Any], ttl: int = 600) -> Any:
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < ttl:
        return hit[1]
    value = loader()
    _cache[key] = (time.monotonic(), value)
    return value


def _teams() -> dict[Any, str]:
    if _service_client is None:
        return {}

    def load() -> dict:
        rows = _service_client.table("teams").select("id,name,city").execute().data or []
        out = {}
        for t in rows:
            name, city = t.get("name") or "", t.get("city") or ""
            out[t["id"]] = name if (not city or city in name) else f"{city} {name}"
        return out

    return _cached("teams", load)


def _bookmakers() -> dict[Any, str]:
    if _service_client is None:
        return {}

    def load() -> dict:
        rows = _service_client.table("bookmakers").select("id,name").execute().data or []
        return {b["id"]: b.get("name") for b in rows}

    return _cached("bookmakers", load)


def _lookup(table: str, cols: str, ids: set) -> dict[Any, dict]:
    if not ids or _service_client is None:
        return {}
    rows = (
        _service_client.table(table).select(cols).in_("id", list(ids)[:200]).execute().data or []
    )
    return {r["id"]: r for r in rows}


def _enrich(rows: list[dict]) -> list[dict]:
    """Add readable labels next to ids. Never raises: on any problem rows are returned as-is."""
    if not rows:
        return rows
    try:
        keys: set[str] = set()
        for r in rows:
            keys.update(r.keys())
        teams = _teams()
        books = _bookmakers()
        players = (
            _lookup("players", "id,name,position", {r["player_id"] for r in rows if r.get("player_id") is not None})
            if "player_id" in keys and "player_name" not in keys else {}
        )
        games = (
            _lookup("games", "id,home_team_id,away_team_id,week,season", {r["game_id"] for r in rows if r.get("game_id") is not None})
            if "game_id" in keys else {}
        )
        for r in rows:
            for src, dst in (("team_id", "team"), ("home_team_id", "home_team"),
                             ("away_team_id", "away_team"), ("opponent_team_id", "opponent")):
                if r.get(src) in teams:
                    r[dst] = teams[r[src]]
            if r.get("bookmaker_id") in books:
                r["bookmaker"] = books[r["bookmaker_id"]]
            if r.get("player_id") in players:
                r["player"] = players[r["player_id"]].get("name")
            g = games.get(r.get("game_id"))
            if g:
                away = teams.get(g.get("away_team_id"), "?")
                home = teams.get(g.get("home_team_id"), "?")
                r["game"] = f"{away} @ {home} (week {g.get('week')}, {g.get('season')})"
    except Exception:
        log.exception("enrich failed")
    return rows


# ---------------------------------------------------------------------------
# Tool: query_data
# ---------------------------------------------------------------------------
def _t_query_data(ctx: ToolContext, a: dict) -> dict:
    name, spec = _table(a.get("table"))
    filters = _clean_filters(name, spec, a.get("filters"))
    match = "any" if a.get("match") == "any" else "all"
    if spec.get("require_filter") and not filters:
        raise ToolError(f"'{name}' is a large table. Add at least one filter (for example game_id or player_id).")

    limit = _int(a.get("limit"), 20, 1, settings.assistant_max_rows)
    virtual = VIRTUAL.get(name, {})
    order_by, desc = a.get("order_by"), bool(a.get("descending"))

    wanted = a.get("columns") or []
    if not isinstance(wanted, list):
        raise ToolError("'columns' must be a list of column names.")
    for c in wanted:
        if c not in spec["columns"] and c not in virtual:
            raise ToolError(f"Unknown column '{c}' for '{name}'. Columns: {', '.join(spec['columns'] + list(virtual))}.")
    if order_by and order_by not in spec["columns"] and order_by not in virtual:
        raise ToolError(f"Cannot order '{name}' by '{order_by}'.")

    needs_virtual = (order_by in virtual) or any(c in virtual for c in wanted)
    real_wanted = [c for c in wanted if c in spec["columns"]]
    fetch_cols = spec["columns"] if (needs_virtual or not real_wanted) else real_wanted

    if order_by in virtual:
        rows, _ = _fetch_all(ctx, name, spec, spec["columns"], filters, match, SORT_ROW_CAP)
        _add_virtual(name, rows)
        rows = [r for r in rows if r.get(order_by) is not None]
        rows.sort(key=lambda r: r[order_by], reverse=desc)
        rows = rows[:limit]
    else:
        rows = _fetch(ctx, name, spec, fetch_cols, filters, match,
                      order=order_by, desc=desc, limit=limit)
        if needs_virtual:
            _add_virtual(name, rows)

    if wanted:
        rows = [{k: r.get(k) for k in wanted} for r in rows]

    result: dict[str, Any] = {"table": name, "row_count": len(rows), "rows": _enrich(rows)}
    if len(rows) >= limit:
        result["note"] = f"Showing {limit} rows; more may exist. Narrow the filters or raise the limit."
    return result


# ---------------------------------------------------------------------------
# Tool: aggregate_data
# ---------------------------------------------------------------------------
def _compute(fn: str, values: list[Any]) -> Any:
    present = [v for v in values if v is not None]
    if fn == "count":
        return len(values)
    if not present:
        return None
    if fn in ("sum", "avg"):
        nums = [float(v) for v in present if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if not nums:
            return None
        return round(sum(nums), 4) if fn == "sum" else round(sum(nums) / len(nums), 4)
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in present):
        return min(present) if fn == "min" else max(present)
    texts = [str(v) for v in present]
    return min(texts) if fn == "min" else max(texts)


def _t_aggregate_data(ctx: ToolContext, a: dict) -> dict:
    name, spec = _table(a.get("table"))
    fn = a.get("function")
    if fn not in ("count", "sum", "avg", "min", "max"):
        raise ToolError("'function' must be one of: count, sum, avg, min, max.")
    virtual = VIRTUAL.get(name, {})
    valid = set(spec["columns"]) | set(virtual)
    column, group_by = a.get("column"), a.get("group_by")
    if fn != "count" and column not in valid:
        raise ToolError(f"'column' is required for {fn}. Columns: {', '.join(sorted(valid))}.")
    if group_by and group_by not in valid:
        raise ToolError(f"Cannot group '{name}' by '{group_by}'.")

    filters = _clean_filters(name, spec, a.get("filters"))
    match = "any" if a.get("match") == "any" else "all"
    if spec.get("require_filter") and not filters:
        raise ToolError(f"'{name}' is a large table. Add at least one filter.")

    if fn == "count" and not group_by:
        query = _db(ctx, spec).table(name).select(spec["columns"][0], count="exact")
        query = _apply_filters(query, ctx, spec, filters, match)
        res = query.limit(1).execute()
        value = res.count if getattr(res, "count", None) is not None else len(res.data or [])
        return {"table": name, "function": "count", "value": value}

    rows, truncated = _fetch_all(ctx, name, spec, spec["columns"], filters, match, AGG_ROW_CAP)
    _add_virtual(name, rows)

    groups: dict[Any, list[Any]] = {}
    for r in rows:
        key = r.get(group_by) if group_by else "all"
        groups.setdefault(key, []).append(r.get(column) if column else 1)

    out = [{"group": k, "value": _compute(fn, v), "rows": len(v)} for k, v in groups.items()]
    result: dict[str, Any] = {
        "table": name, "function": fn, "column": column, "group_by": group_by,
        "rows_scanned": len(rows),
    }
    if truncated:
        result["warning"] = f"Only the first {AGG_ROW_CAP} matching rows were scanned. Add filters for exact results."

    if not group_by:
        result["value"] = out[0]["value"] if out else None
        return result

    out.sort(key=lambda g: (g["value"] is None, -(g["value"] if isinstance(g["value"], (int, float)) else 0)))
    top = _int(a.get("top"), 25, 1, 50)
    shaped = [{group_by: g["group"], "value": g["value"], "rows": g["rows"]} for g in out[:top]]
    result["results"] = _enrich(shaped)
    return result


# ---------------------------------------------------------------------------
# Tool: find_entity
# ---------------------------------------------------------------------------
def _t_find_entity(ctx: ToolContext, a: dict) -> dict:
    kind = a.get("kind")
    text = str(a.get("query") or "").strip()
    if kind not in ("player", "team"):
        raise ToolError("'kind' must be 'player' or 'team'.")
    if len(text) < 2:
        raise ToolError("'query' must be at least 2 characters.")
    if _service_client is None:
        raise ToolError("The database is not configured.")

    pattern = _like(text)
    if kind == "player":
        base = _service_client.table("players").select("id,name,position,team_id,is_active")
        rows = base.ilike("name", pattern).order("is_active", desc=True, nullsfirst=False).limit(10).execute().data or []
        parts = text.split()
        if not rows and len(parts) > 1:
            rows = (
                _service_client.table("players").select("id,name,position,team_id,is_active")
                .ilike("last_name", _like(parts[-1])).limit(10).execute().data or []
            )
    else:
        clause = ",".join(f"{c}.ilike.{_quote(pattern)}" for c in ("name", "city", "abbreviation"))
        rows = (
            _service_client.table("teams").select("id,name,city,abbreviation,conference,division")
            .or_(clause).limit(10).execute().data or []
        )
    return {"kind": kind, "matches": _enrich(rows)}


# ---------------------------------------------------------------------------
# File tools
# ---------------------------------------------------------------------------
def _t_list_files(ctx: ToolContext, a: dict) -> dict:
    return {"files": files.list_files(ctx.user_client, limit=50)}


def _t_read_file(ctx: ToolContext, a: dict) -> dict:
    row = files.get_file(ctx.user_client, str(a.get("file_id") or ""))
    text = row.get("extracted_text")
    if not text:
        note = (
            "This is an image. Images can only be viewed when attached to the user's message."
            if files.is_image(row)
            else "No readable text could be extracted from this file type."
        )
        return {"name": row["name"], "note": note}
    offset = _int(a.get("offset"), 0, 0, len(text))
    size = _int(a.get("max_chars"), 20000, 1000, 40000)
    return {
        "name": row["name"],
        "total_chars": len(text),
        "offset": offset,
        "text": text[offset: offset + size],
        "has_more": offset + size < len(text),
    }


def _t_create_file(ctx: ToolContext, a: dict) -> dict:
    row = files.create_generated_file(
        ctx.user_client,
        ctx.user_id,
        filename=str(a.get("filename") or "export"),
        file_format=str(a.get("file_format") or ""),
        text=a.get("text"),
        rows=a.get("rows"),
        conversation_id=ctx.conversation_id,
    )
    ctx.generated_files.append(row)
    return {
        "file_id": row["id"],
        "name": row["name"],
        "status": "Created. The user sees a download button under your reply. Do not paste links.",
    }


_HANDLERS: dict[str, Callable[[ToolContext, dict], dict]] = {
    "query_data": _t_query_data,
    "aggregate_data": _t_aggregate_data,
    "find_entity": _t_find_entity,
    "list_files": _t_list_files,
    "read_file": _t_read_file,
    "create_file": _t_create_file,
}

TOOL_LABELS = {
    "query_data": "Looking up your data...",
    "aggregate_data": "Crunching the numbers...",
    "find_entity": "Finding the player or team...",
    "list_files": "Checking your files...",
    "read_file": "Reading your file...",
    "create_file": "Creating your file...",
}


# ---------------------------------------------------------------------------
# Tool definitions shown to the model
# ---------------------------------------------------------------------------
def _tool(name: str, description: str, properties: dict, required: tuple = ()) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": list(required)},
        },
    }


_TABLE_PROP = {"type": "string", "enum": list(TABLES), "description": "Table to read."}

_FILTERS_PROP = {
    "type": "array",
    "description": 'Conditions. Example: [{"column":"week","op":"eq","value":"5"}]',
    "items": {
        "type": "object",
        "properties": {
            "column": {"type": "string"},
            "op": {"type": "string", "enum": _OPS},
            "value": {
                "type": "string",
                "description": (
                    "Always a string. Numbers as digits ('5'), booleans 'true'/'false', "
                    "dates ISO ('2026-10-04'). For 'in' use comma-separated values. "
                    "For 'ilike' pass a name fragment (matched anywhere, ignoring case). "
                    "For 'is_null' pass 'true' or 'false'."
                ),
            },
        },
        "required": ["column", "op", "value"],
    },
}

_MATCH_PROP = {
    "type": "string",
    "enum": ["all", "any"],
    "description": "'all' = every filter must match (default). 'any' = at least one filter matches.",
}

TOOL_DEFS: list[dict] = [
    _tool(
        "query_data",
        "Read rows from one allowed table. Use for lookups, rankings ('highest', 'latest', "
        "'top 5') and lists. Leave 'columns' empty to get all columns with readable team, "
        "player and bookmaker names added.",
        {
            "table": _TABLE_PROP,
            "columns": {"type": "array", "items": {"type": "string"},
                        "description": "Optional. Only these columns. Usually leave empty."},
            "filters": _FILTERS_PROP,
            "match": _MATCH_PROP,
            "order_by": {"type": "string", "description": "Column to sort by (computed columns like total_points work too)."},
            "descending": {"type": "boolean", "description": "true for highest / latest first."},
            "limit": {"type": "integer", "description": f"Rows to return (max {settings.assistant_max_rows}). Default 20."},
        },
        ("table",),
    ),
    _tool(
        "aggregate_data",
        "Count, sum, average, min or max over a table, optionally grouped (for example "
        "average total_points per season, or number of injured players per team).",
        {
            "table": _TABLE_PROP,
            "function": {"type": "string", "enum": ["count", "sum", "avg", "min", "max"]},
            "column": {"type": "string", "description": "Column to aggregate (not needed for count)."},
            "group_by": {"type": "string", "description": "Optional column to group by."},
            "filters": _FILTERS_PROP,
            "match": _MATCH_PROP,
            "top": {"type": "integer", "description": "Max groups to return (default 25)."},
        },
        ("table", "function"),
    ),
    _tool(
        "find_entity",
        "Find a player or team by name to get its id (needed to filter other tables by player_id or team_id).",
        {
            "kind": {"type": "string", "enum": ["player", "team"]},
            "query": {"type": "string", "description": "Name fragment, e.g. 'Mahomes' or 'Chiefs'."},
        },
        ("kind", "query"),
    ),
    _tool("list_files", "List the files this user has uploaded or the assistant has created.", {}),
    _tool(
        "read_file",
        "Read the text of one of the user's files by id. Use 'offset' to continue a long file.",
        {
            "file_id": {"type": "string"},
            "offset": {"type": "integer", "description": "Character position to start from. Default 0."},
            "max_chars": {"type": "integer", "description": "Characters to return (1000-40000). Default 20000."},
        },
        ("file_id",),
    ),
    _tool(
        "create_file",
        "Create a downloadable file for the user: xlsx (needs 'rows'), csv (rows or text), "
        "or txt / md / json / html (needs 'text'). Use when the user asks to export, "
        "download or save something.",
        {
            "filename": {"type": "string", "description": "Name without path, e.g. 'week5_injuries'."},
            "file_format": {"type": "string", "enum": list(files.GENERATED_FORMATS)},
            "text": {"type": "string", "description": "Full file content for txt / md / json / html (or csv)."},
            "rows": {
                "type": "array",
                "description": "For xlsx / csv: a list of rows, first row = column headers.",
                "items": {"type": "array", "items": {"type": ["string", "number", "boolean", "null"]}},
            },
        },
        ("filename", "file_format"),
    ),
]


# ---------------------------------------------------------------------------
# Entry point used by the agent loop
# ---------------------------------------------------------------------------
def _dump(result: Any) -> str:
    text = json.dumps(result, default=str, ensure_ascii=False)
    if len(text) > MAX_TOOL_CHARS:
        text = text[:MAX_TOOL_CHARS] + ' ...[truncated: ask for fewer rows or columns]'
    return text


def run_tool(ctx: ToolContext, name: str, raw_args: str) -> str:
    """Run one tool call and return a JSON string for the model. Never raises."""
    handler = _HANDLERS.get(name)
    if handler is None:
        return _dump({"error": f"Unknown tool '{name}'."})
    try:
        args = json.loads(raw_args) if raw_args and raw_args.strip() else {}
        if not isinstance(args, dict):
            raise ToolError("Arguments must be a JSON object.")
        result = handler(ctx, args)
    except ToolError as exc:
        result = {"error": str(exc)}
    except files.FileError as exc:
        result = {"error": exc.message}
    except json.JSONDecodeError:
        result = {"error": "Arguments were not valid JSON."}
    except Exception as exc:  # noqa: BLE001
        message = getattr(exc, "message", None)
        if exc.__class__.__name__ == "APIError" and message:
            result = {"error": f"Database rejected the query: {str(message)[:200]}"}
        else:
            log.exception("tool %s failed", name)
            result = {"error": "The tool failed. Try a simpler request."}
    return _dump(result)


def consume_generated_files(ctx: ToolContext) -> list[dict]:
    """
    Return any files created by tools during this turn and clear the list
    so the same files are not emitted twice.
    """
    created = list(ctx.generated_files)
    ctx.generated_files.clear()
    return created