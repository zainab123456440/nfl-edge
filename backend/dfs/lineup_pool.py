"""Generate a diverse pool of DraftKings Showdown lineups."""
from __future__ import annotations

from dataclasses import dataclass, field

from .contest_rules import SHOWDOWN, ContestRules
from .models import DKPlayer
from .optimizer import (
    Lineup,
    OptimizerError,
    build_lineup,
    validate_lineup,
)
from .projections import Projection


@dataclass(frozen=True)
class PoolSettings:
    lineup_count: int = 150

    # Maximum percentage of lineups in which one player may appear.
    max_player_exposure: float = 0.70

    # Maximum percentage of lineups in which one player may be captain.
    max_captain_exposure: float = 0.40

    # Number of different players we try to use across the pool.
    min_unique_players: int = 8

    # Safety limit if the constraints make a lineup difficult to find.
    attempts_per_lineup: int = 100

    # How strongly frequently-used players are penalized.
    exposure_penalty: float = 8.0

    # How strongly frequently-used captains are penalized.
    captain_penalty: float = 12.0

    # Never allow the same exact lineup more than this many times.
    max_duplicate_lineups: int = 1


@dataclass
class LineupPool:
    lineups: list[Lineup] = field(default_factory=list)
    player_exposure: dict[str, int] = field(default_factory=dict)
    captain_exposure: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.lineups)

    @property
    def unique_player_count(self) -> int:
        return len(self.player_exposure)


def _lineup_key(lineup: Lineup) -> tuple:
    return (
        lineup.captain.player_key,
        tuple(
            sorted(
                p.player_key
                for p in lineup.flex
            )
        ),
    )


def _max_player_count(
    settings: PoolSettings,
) -> int:
    return max(
        1,
        int(settings.lineup_count * settings.max_player_exposure),
    )


def _max_captain_count(
    settings: PoolSettings,
) -> int:
    return max(
        1,
        int(settings.lineup_count * settings.max_captain_exposure),
    )


def _player_penalties(
    players: list[DKPlayer],
    counts: dict[str, int],
    settings: PoolSettings,
) -> dict[str, float]:
    penalties = {}

    max_count = _max_player_count(settings)

    for player in players:
        count = counts.get(player.player_key, 0)

        if count >= max_count:
            penalties[player.player_key] = 1_000_000.0
        else:
            penalties[player.player_key] = (
                count * settings.exposure_penalty
            )

    return penalties


def _captain_penalties(
    players: list[DKPlayer],
    counts: dict[str, int],
    settings: PoolSettings,
) -> dict[str, float]:
    penalties = {}

    max_count = _max_captain_count(settings)

    for player in players:
        count = counts.get(player.player_key, 0)

        if count >= max_count:
            penalties[player.player_key] = 1_000_000.0
        else:
            penalties[player.player_key] = (
                count * settings.captain_penalty
            )

    return penalties


def _candidate_is_allowed(
    lineup: Lineup,
    pool: LineupPool,
    settings: PoolSettings,
) -> bool:
    max_player = _max_player_count(settings)
    max_captain = _max_captain_count(settings)

    if pool.captain_exposure.get(
        lineup.captain.player_key,
        0,
    ) >= max_captain:
        return False

    for player in lineup.players:
        if pool.player_exposure.get(
            player.player_key,
            0,
        ) >= max_player:
            return False

    return True


def _record_lineup(
    lineup: Lineup,
    pool: LineupPool,
) -> None:
    pool.lineups.append(lineup)

    captain_key = lineup.captain.player_key

    pool.captain_exposure[captain_key] = (
        pool.captain_exposure.get(captain_key, 0) + 1
    )

    for player in lineup.players:
        key = player.player_key

        pool.player_exposure[key] = (
            pool.player_exposure.get(key, 0) + 1
        )


def generate_lineup_pool(
    players: list[DKPlayer],
    projections: dict[str, Projection],
    settings: PoolSettings | None = None,
    rules: ContestRules = SHOWDOWN,
    *,
    seed: int | None = None,
) -> LineupPool:
    """Generate a diverse, exposure-controlled lineup pool."""

    settings = settings or PoolSettings()

    if settings.lineup_count <= 0:
        raise ValueError("lineup_count must be greater than zero.")

    if not 0 < settings.max_player_exposure <= 1:
        raise ValueError(
            "max_player_exposure must be between 0 and 1."
        )

    if not 0 < settings.max_captain_exposure <= 1:
        raise ValueError(
            "max_captain_exposure must be between 0 and 1."
        )

    pool = LineupPool()

    # `seed` is accepted so the API can later expose deterministic runs.
    # The current diversity mechanism is deterministic because it is driven
    # by exposure penalties rather than random shuffling.
    _ = seed

    used_keys: dict[tuple, int] = {}

    for _index in range(settings.lineup_count):
        generated = False

        for _attempt in range(settings.attempts_per_lineup):
            player_penalties = _player_penalties(
                players,
                pool.player_exposure,
                settings,
            )

            captain_penalties = _captain_penalties(
                players,
                pool.captain_exposure,
                settings,
            )

            try:
                lineup = build_lineup(
                    players,
                    projections,
                    rules,
                    player_penalties=player_penalties,
                    captain_penalties=captain_penalties,
                )
            except OptimizerError:
                break

            errors = validate_lineup(lineup, rules)

            if errors:
                break

            key = _lineup_key(lineup)
            duplicates = used_keys.get(key, 0)

            if duplicates >= settings.max_duplicate_lineups:
                # Make the players in this lineup significantly more
                # expensive for the next optimization pass.
                for player in lineup.players:
                    pool.player_exposure[player.player_key] = (
                        pool.player_exposure.get(
                            player.player_key,
                            0,
                        )
                    )

                # Increase the relevant captain penalty.
                captain_key = lineup.captain.player_key
                pool.captain_exposure[captain_key] = (
                    pool.captain_exposure.get(
                        captain_key,
                        0,
                    )
                )

                # Temporarily make this exact combination unattractive
                # by adding an additional exposure pressure.
                for player in lineup.players:
                    player_penalties[player.player_key] = (
                        player_penalties.get(
                            player.player_key,
                            0.0,
                        ) + 25.0
                    )

                captain_penalties[lineup.captain.player_key] = (
                    captain_penalties.get(
                        lineup.captain.player_key,
                        0.0,
                    ) + 50.0
                )

                # Re-run optimizer with stronger penalties.
                try:
                    lineup = build_lineup(
                        players,
                        projections,
                        rules,
                        player_penalties=player_penalties,
                        captain_penalties=captain_penalties,
                    )
                except OptimizerError:
                    break

                key = _lineup_key(lineup)

                if used_keys.get(key, 0) >= settings.max_duplicate_lineups:
                    continue

            if not _candidate_is_allowed(
                lineup,
                pool,
                settings,
            ):
                continue

            _record_lineup(lineup, pool)
            used_keys[key] = used_keys.get(key, 0) + 1
            generated = True
            break

        if not generated:
            break

    if pool.count < settings.lineup_count:
        pool.warnings.append(
            f"Generated {pool.count} of "
            f"{settings.lineup_count} requested lineups. "
            "The remaining lineups could not satisfy the current "
            "salary, team, projection, uniqueness, or exposure constraints."
        )

    if pool.unique_player_count < settings.min_unique_players:
        pool.warnings.append(
            f"Only {pool.unique_player_count} unique players were used; "
            f"target was at least {settings.min_unique_players}."
        )

    return pool


def pool_summary(pool: LineupPool) -> dict:
    return {
        "requested": None,
        "generated": pool.count,
        "unique_players": pool.unique_player_count,
        "player_exposure": dict(
            sorted(
                pool.player_exposure.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "captain_exposure": dict(
            sorted(
                pool.captain_exposure.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ),
        "warnings": list(pool.warnings),
    }