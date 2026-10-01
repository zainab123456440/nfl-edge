"""Export generated DraftKings Showdown lineups to CSV."""
from __future__ import annotations

import csv
import io

from .contest_rules import SHOWDOWN, ContestRules
from .lineup_pool import LineupPool
from .optimizer import Lineup


def _lineup_row(
    lineup: Lineup,
    rules: ContestRules,
) -> dict[str, str | int | float]:
    """Convert one internal lineup into a DraftKings-style row."""

    slots = list(rules.slots)
    players = list(lineup.players)

    row: dict[str, str | int | float] = {}

    for index, slot in enumerate(slots):
        player = players[index]

        row[slot] = player.dk_id

    row["Salary"] = lineup.salary
    row["ProjectedPoints"] = round(lineup.projected_points, 2)

    return row


def export_lineups_csv(
    lineups: list[Lineup],
    rules: ContestRules = SHOWDOWN,
) -> str:
    """Return generated lineups as CSV text."""

    if not lineups:
        raise ValueError("Cannot export an empty lineup list.")

    output = io.StringIO()

    fieldnames = [
        *rules.slots,
        "Salary",
        "ProjectedPoints",
    ]

    writer = csv.DictWriter(
        output,
        fieldnames=fieldnames,
        lineterminator="\n",
    )

    writer.writeheader()

    for lineup in lineups:
        writer.writerow(
            _lineup_row(
                lineup,
                rules,
            )
        )

    return output.getvalue()


def export_pool_csv(
    pool: LineupPool,
    rules: ContestRules = SHOWDOWN,
) -> str:
    """Export an entire lineup pool."""

    if not pool.lineups:
        raise ValueError("Cannot export an empty lineup pool.")

    return export_lineups_csv(
        pool.lineups,
        rules,
    )


def export_pool_bytes(
    pool: LineupPool,
    rules: ContestRules = SHOWDOWN,
) -> bytes:
    """Return the lineup pool as UTF-8 CSV bytes."""

    return export_pool_csv(
        pool,
        rules,
    ).encode("utf-8")