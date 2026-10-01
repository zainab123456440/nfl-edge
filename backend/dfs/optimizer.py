"""DraftKings Showdown lineup optimizer.

The optimizer builds one valid lineup at a time.  Optional player/captain
penalties are used by lineup_pool.py to create a diverse lineup set.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import isfinite
from typing import Optional

from .contest_rules import SHOWDOWN, ContestRules
from .models import DKPlayer
from .projections import Projection


@dataclass(frozen=True)
class LineupPlayer:
    player_key: str
    name: str
    position: str
    team: str
    slot: str
    dk_id: str
    salary: int
    projection: float


@dataclass(frozen=True)
class Lineup:
    captain: LineupPlayer
    flex: tuple[LineupPlayer, ...]
    salary: int
    projected_points: float

    @property
    def players(self) -> tuple[LineupPlayer, ...]:
        return (self.captain, *self.flex)

    @property
    def player_keys(self) -> tuple[str, ...]:
        return tuple(p.player_key for p in self.players)

    @property
    def teams(self) -> set[str]:
        return {p.team for p in self.players}


class OptimizerError(Exception):
    """Raised when no valid lineup can be constructed."""


def _usable_players(
    players: list[DKPlayer],
    projections: dict[str, Projection],
) -> list[DKPlayer]:
    result = []

    for player in players:
        projection = projections.get(player.player_key)

        if projection is None:
            continue

        if projection.excluded:
            continue

        if not isfinite(projection.points):
            continue

        if projection.points < 0:
            continue

        result.append(player)

    return result


def _captain_projection(
    player: DKPlayer,
    projection: Projection,
    rules: ContestRules,
) -> float:
    return projection.points * rules.captain_multiplier


def _make_captain(
    player: DKPlayer,
    projection: Projection,
    rules: ContestRules,
) -> LineupPlayer:
    return LineupPlayer(
        player_key=player.player_key,
        name=player.name,
        position=player.position,
        team=player.team,
        slot=rules.captain_slot or "CPT",
        dk_id=player.cpt_id,
        salary=player.cpt_salary,
        projection=_captain_projection(player, projection, rules),
    )


def _make_flex(
    player: DKPlayer,
    projection: Projection,
) -> LineupPlayer:
    return LineupPlayer(
        player_key=player.player_key,
        name=player.name,
        position=player.position,
        team=player.team,
        slot="FLEX",
        dk_id=player.flex_id,
        salary=player.flex_salary,
        projection=projection.points,
    )


def _meets_team_requirement(
    lineup_players: list[LineupPlayer],
    rules: ContestRules,
) -> bool:
    teams = {}

    for player in lineup_players:
        teams[player.team] = teams.get(player.team, 0) + 1

    if len(teams) < 2:
        return False

    return all(
        count >= rules.min_players_per_team
        for count in teams.values()
    )


def _score_candidate(
    lineup: Lineup,
    player_penalties: Optional[dict[str, float]],
    captain_penalties: Optional[dict[str, float]],
) -> float:
    score = lineup.projected_points

    player_penalties = player_penalties or {}
    captain_penalties = captain_penalties or {}

    for player in lineup.players:
        score -= player_penalties.get(player.player_key, 0.0)

    score -= captain_penalties.get(lineup.captain.player_key, 0.0)

    return score


def build_lineup(
    players: list[DKPlayer],
    projections: dict[str, Projection],
    rules: ContestRules = SHOWDOWN,
    *,
    player_penalties: Optional[dict[str, float]] = None,
    captain_penalties: Optional[dict[str, float]] = None,
) -> Lineup:
    """Build the highest-scoring valid lineup.

    Penalties are optional. They are used by the lineup-pool generator to
    discourage repeatedly selecting the same players.
    """

    usable = _usable_players(players, projections)

    if len(usable) < rules.roster_size:
        raise OptimizerError(
            f"Only {len(usable)} usable players are available; "
            f"{rules.roster_size} are required."
        )

    best: Optional[Lineup] = None
    best_score = float("-inf")

    for captain_player in usable:
        captain_projection = projections[captain_player.player_key]

        captain = _make_captain(
            captain_player,
            captain_projection,
            rules,
        )

        flex_candidates = [
            p for p in usable
            if p.player_key != captain_player.player_key
        ]

        for flex_players in combinations(
            flex_candidates,
            rules.flex_slots,
        ):
            lineup_players = [
                captain,
                *[
                    _make_flex(
                        p,
                        projections[p.player_key],
                    )
                    for p in flex_players
                ],
            ]

            if not _meets_team_requirement(
                lineup_players,
                rules,
            ):
                continue

            salary = sum(p.salary for p in lineup_players)

            if salary > rules.salary_cap:
                continue

            projected_points = sum(
                p.projection for p in lineup_players
            )

            lineup = Lineup(
                captain=captain,
                flex=tuple(
                    sorted(
                        lineup_players[1:],
                        key=lambda p: (
                            -p.projection,
                            -p.salary,
                            p.name,
                        ),
                    )
                ),
                salary=salary,
                projected_points=projected_points,
            )

            score = _score_candidate(
                lineup,
                player_penalties,
                captain_penalties,
            )

            if best is None:
                best = lineup
                best_score = score
                continue

            if score > best_score:
                best = lineup
                best_score = score
                continue

            if score == best_score:
                if lineup.projected_points > best.projected_points:
                    best = lineup
                    best_score = score
                elif (
                    lineup.projected_points == best.projected_points
                    and lineup.salary > best.salary
                ):
                    best = lineup
                    best_score = score

    if best is None:
        raise OptimizerError(
            "No valid Showdown lineup could be constructed under "
            "the salary and team constraints."
        )

    return best


def validate_lineup(
    lineup: Lineup,
    rules: ContestRules = SHOWDOWN,
) -> list[str]:
    """Return validation errors. Empty list means valid."""

    errors: list[str] = []

    players = lineup.players

    if len(players) != rules.roster_size:
        errors.append(
            f"Expected {rules.roster_size} roster spots, "
            f"got {len(players)}."
        )

    captains = [
        p for p in players
        if p.slot == rules.captain_slot
    ]

    if len(captains) != 1:
        errors.append(
            f"Expected exactly one {rules.captain_slot}, "
            f"got {len(captains)}."
        )

    flex_count = sum(
        1 for p in players
        if p.slot == "FLEX"
    )

    if flex_count != rules.flex_slots:
        errors.append(
            f"Expected {rules.flex_slots} FLEX players, "
            f"got {flex_count}."
        )

    keys = [p.player_key for p in players]

    if len(keys) != len(set(keys)):
        errors.append("A player appears more than once.")

    actual_salary = sum(p.salary for p in players)

    if actual_salary != lineup.salary:
        errors.append(
            f"Salary mismatch: stored={lineup.salary}, "
            f"actual={actual_salary}."
        )

    if lineup.salary > rules.salary_cap:
        errors.append(
            f"Salary {lineup.salary} exceeds cap "
            f"{rules.salary_cap}."
        )

    if not _meets_team_requirement(players, rules):
        errors.append(
            "Lineup does not satisfy the minimum team requirement."
        )

    actual_projection = sum(
        p.projection for p in players
    )

    if abs(actual_projection - lineup.projected_points) > 1e-6:
        errors.append(
            "Projected-points total does not match player projections."
        )

    return errors