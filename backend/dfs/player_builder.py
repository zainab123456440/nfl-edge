"""Turns raw DK rows into one DKPlayer per player (CPT + FLEX versions paired)."""
from __future__ import annotations

from collections import defaultdict

from .contest_rules import SHOWDOWN, get_rules
from .dk_parser import DKParseError, detect_contest_type, parse_dk_csv, parse_game_info
from .names import make_player_key
from .models import ContestType, DKPlayer, DKRow, ParsedSlate


def build_showdown_players(rows: list[DKRow]) -> tuple[list[DKPlayer], list[str]]:
    warnings: list[str] = []
    groups: dict[str, dict[str, list[DKRow]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        groups[make_player_key(r.name, r.team)][r.roster_position].append(r)

    players: list[DKPlayer] = []
    mult = SHOWDOWN.captain_multiplier
    for key, by_slot in groups.items():
        cpts, flexes = by_slot.get("CPT", []), by_slot.get("FLEX", [])
        label = (cpts or flexes)[0].name
        if not cpts or not flexes:
            warnings.append(f"{label}: missing {'CPT' if not cpts else 'FLEX'} row, skipped.")
            continue
        if len(cpts) > 1 or len(flexes) > 1:
            warnings.append(f"{label}: duplicate rows for the same player, using the first of each.")
        cpt, flex = cpts[0], flexes[0]
        if cpt.salary != round(flex.salary * mult):
            warnings.append(
                f"{label}: CPT salary {cpt.salary} is not {mult}x FLEX salary {flex.salary}."
            )
        players.append(DKPlayer(
            player_key=key,
            name=flex.name,
            position=flex.position,
            team=flex.team,
            flex_id=flex.dk_id,
            flex_salary=flex.salary,
            cpt_id=cpt.dk_id,
            cpt_salary=cpt.salary,
            avg_points=max(flex.avg_points, cpt.avg_points),
        ))
    players.sort(key=lambda p: (-p.flex_salary, p.name))
    return players, warnings


def load_slate(content: bytes | str) -> ParsedSlate:
    """Full pipeline: raw file -> validated ParsedSlate."""
    template, rows = parse_dk_csv(content)
    contest_type = detect_contest_type(rows)
    get_rules(contest_type)  # raises UnsupportedContest for Classic (for now)

    games = {r.game_info for r in rows}
    if len(games) != 1:
        raise DKParseError(f"A Showdown file must contain exactly one game, found {len(games)}.")
    game = parse_game_info(next(iter(games)))

    players, warnings = build_showdown_players(rows)
    if not players:
        raise DKParseError("No complete CPT/FLEX player pairs found.")

    teams = {p.team for p in players}
    if teams != {game.home_team, game.away_team}:
        warnings.append(f"Teams in rows {sorted(teams)} differ from game info {game.raw!r}.")

    expected = list(SHOWDOWN.slots)
    if template and template != expected:
        warnings.append(f"Template row {template} differs from the expected Showdown layout.")

    return ParsedSlate(
        contest_type=ContestType.SHOWDOWN,
        slots=template or expected,
        game=game,
        players=players,
        warnings=warnings,
    )