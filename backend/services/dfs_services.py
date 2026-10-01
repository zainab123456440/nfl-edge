"""DFS service layer.

Handles:
- DraftKings slate analysis
- lineup generation
- generated-run metadata
- CSV export
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from dfs.game_context import build_game_context
from dfs.injuries import availability_for, latest_availability
from dfs.lineup_pool import PoolSettings, generate_lineup_pool, pool_summary
from dfs.player_builder import load_slate
from dfs.player_matcher import Candidate, match_players
from dfs.projections import project_slate
from dfs.exporter import export_pool_csv
from services import dfs_queries as q


# Temporary in-process run storage.
#
# This is intentionally simple for the first API integration.
# Later this can move to Supabase/Postgres/Storage for persistence.
_GENERATED_RUNS: dict[str, dict] = {}


def _build_candidates(game_id, team_ids, by_id) -> list:
    """Everyone who could be a CSV player."""

    with_props = q.props_player_ids(game_id) if game_id else set()

    rows = {}

    for r in q.roster_players(team_ids):
        rows[r["id"]] = r

    missing = [
        i for i in with_props
        if i not in rows
    ]

    for r in q.players_by_ids(missing):
        rows[r["id"]] = r

    return [
        Candidate(
            id=r["id"],
            name=r["name"],
            position=r.get("position"),
            team=by_id.get(r.get("team_id")),
            has_props=r["id"] in with_props,
            is_active=bool(r.get("is_active", True)),
        )
        for r in rows.values()
        if r.get("name")
    ]


def analyze_slate(content: bytes) -> dict:
    """Parse and analyze a DraftKings salary CSV."""

    slate = load_slate(content)

    game = slate.game
    warnings = list(slate.warnings)

    by_abbr, by_id = q.get_teams()

    home_id = q.resolve_team_id(
        game.home_team,
        by_abbr,
    )

    away_id = q.resolve_team_id(
        game.away_team,
        by_abbr,
    )

    db_game = None
    game_id = None

    if home_id is None or away_id is None:
        missing_team = (
            game.home_team
            if home_id is None
            else game.away_team
        )

        warnings.append(
            f"Team not found in database: {missing_team}."
        )

    else:
        games = q.find_game(
            home_id,
            away_id,
            game.kickoff_utc,
        )

        if not games:
            warnings.append(
                "No matching game found in the games table "
                "near this kickoff time."
            )

        else:
            db_game = games[0]
            game_id = db_game["id"]

            if len(games) > 1:
                warnings.append(
                    f"{len(games)} games matched; "
                    "using the one closest to kickoff."
                )

    team_ids = [
        i for i in (home_id, away_id)
        if i
    ]

    candidates = (
        _build_candidates(
            game_id,
            team_ids,
            by_id,
        )
        if team_ids
        else []
    )

    report = match_players(
        slate.players,
        candidates,
    )

    cand_by_id = {
        c.id: c
        for c in candidates
    }

    ctx = (
        build_game_context(
            q.game_odds(game_id)
        )
        if game_id
        else None
    )

    matched_ids = [
        p.supabase_player_id
        for p in slate.players
        if p.supabase_player_id
    ]

    inj_table, inj_warn = latest_availability(
        q.latest_injury_rows(matched_ids)
    )

    warnings += inj_warn

    availability = {
        p.player_key: availability_for(
            p.supabase_player_id,
            p.player_key,
            inj_table,
        )
        for p in slate.players
    }

    props = (
        q.game_props(game_id)
        if game_id
        else {}
    )

    projections, proj_info = project_slate(
        slate.players,
        props,
        game.home_team,
        game.away_team,
        ctx.home_implied if ctx else None,
        ctx.away_implied if ctx else None,
        availability,
    )

    players = []

    for p in slate.players:
        av = availability[p.player_key]
        pj = projections[p.player_key]

        players.append({
            "name": p.name,
            "position": p.position,
            "team": p.team,
            "flex_salary": p.flex_salary,
            "cpt_salary": p.cpt_salary,
            "avg_points": p.avg_points,
            "supabase_player_id": p.supabase_player_id,
            "match_method": p.match_method,
            "has_props": bool(
                p.supabase_player_id
                and cand_by_id.get(
                    p.supabase_player_id
                )
                and cand_by_id[
                    p.supabase_player_id
                ].has_props
            ),
            "injury_status": av.status or None,
            "excluded_by_injury": av.excluded,
            "projection": {
                "points": pj.points,
                "std": pj.std,
                "tier": pj.tier,
                "excluded": pj.excluded,
                "reason": pj.reason,
                "components": pj.components,
                "notes": pj.notes,
            },
        })

    players.sort(
        key=lambda x: -x["projection"]["points"]
    )

    return {
        "contest": slate.contest_type.value,
        "slots": slate.slots,
        "game": {
            "raw": game.raw,
            "away": game.away_team,
            "home": game.home_team,
            "kickoff_utc": game.kickoff_utc.isoformat(),
            "db_game_id": game_id,
            "db_status": (
                db_game["status"]
                if db_game
                else None
            ),
        },
        "match": {
            "summary": report.summary(),
            "needs_attention": [
                {
                    "name": r.dk_name,
                    "team": r.team,
                    "position": r.position,
                    "status": r.status,
                    "note": r.note,
                }
                for r in report.needs_attention
            ],
        },
        "game_context": (
            None
            if ctx is None
            else {
                "total": ctx.total,
                "home_spread": ctx.home_spread,
                "home_implied": ctx.home_implied,
                "away_implied": ctx.away_implied,
                "home_win_prob": ctx.home_win_prob,
                "away_win_prob": ctx.away_win_prob,
                "books_used": ctx.books_used,
                "warnings": ctx.warnings,
            }
        ),
        "projection_summary": proj_info,
        "players": players,
        "warnings": warnings,
    }


def generate_lineups(
    content: bytes,
    lineup_count: int = 150,
    max_player_exposure: float = 0.70,
    max_captain_exposure: float = 0.40,
    seed: int | None = None,
) -> dict:
    """Analyze a DK salary file and generate a lineup pool."""

    slate = load_slate(content)

    analysis = analyze_slate(content)

    player_map = {
        p["name"]: p
        for p in analysis["players"]
    }

    # Reconstruct the projections from the analysis response.
    # We use the original slate players so all DK IDs/salaries remain intact.
    projections = {}

    for player in slate.players:
        analyzed = player_map.get(player.name)

        if analyzed is None:
            continue

        projection_data = analyzed["projection"]

        from dfs.projections import Projection

        projections[player.player_key] = Projection(
            player_key=player.player_key,
            points=float(
                projection_data["points"]
            ),
            std=float(
                projection_data["std"]
            ),
            tier=int(
                projection_data["tier"]
            ),
            excluded=bool(
                projection_data["excluded"]
            ),
            reason=projection_data["reason"],
            components=projection_data["components"],
            notes=projection_data["notes"],
        )

    settings = PoolSettings(
        lineup_count=lineup_count,
        max_player_exposure=max_player_exposure,
        max_captain_exposure=max_captain_exposure,
    )

    pool = generate_lineup_pool(
        slate.players,
        projections,
        settings=settings,
        seed=seed,
    )

    csv_text = export_pool_csv(pool)

    run_id = str(uuid4())

    now = datetime.now(timezone.utc)

    metadata = {
        "run_id": run_id,
        "created_at": now.isoformat(),
        "contest": slate.contest_type.value,
        "game": {
            "raw": slate.game.raw,
            "away": slate.game.away_team,
            "home": slate.game.home_team,
            "kickoff_utc": slate.game.kickoff_utc.isoformat(),
        },
        "requested_lineups": lineup_count,
        "generated_lineups": pool.count,
        "unique_players": pool.unique_player_count,
        "max_player_exposure": max_player_exposure,
        "max_captain_exposure": max_captain_exposure,
        "summary": pool_summary(pool),
        "analysis": analysis,
        "warnings": [
            *analysis.get("warnings", []),
            *pool.warnings,
        ],
    }

    _GENERATED_RUNS[run_id] = {
        "metadata": metadata,
        "csv": csv_text,
    }

    return metadata


def get_generated_run(run_id: str) -> dict | None:
    """Return stored run metadata and CSV, if it exists."""

    return _GENERATED_RUNS.get(run_id)


def get_generated_run_csv(run_id: str) -> str | None:
    """Return generated CSV for a run."""

    run = _GENERATED_RUNS.get(run_id)

    if run is None:
        return None

    return run["csv"]