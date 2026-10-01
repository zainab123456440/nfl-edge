"""Contest rules. The optimizer reads these instead of hardcoding numbers,
so adding Classic later means adding one more ContestRules entry."""
from __future__ import annotations

from dataclasses import dataclass

from .models import ContestType


@dataclass(frozen=True)
class ContestRules:
    contest_type: ContestType
    salary_cap: int
    slots: tuple[str, ...]        # order matters: this is the export column order
    captain_slot: str | None      # slot that gets the multiplier
    captain_multiplier: float
    min_players_per_team: int     # DraftKings requires players from both teams in Showdown
    max_lineups_per_file: int = 500

    @property
    def roster_size(self) -> int:
        return len(self.slots)

    @property
    def flex_slots(self) -> int:
        return sum(1 for s in self.slots if s != self.captain_slot)


SHOWDOWN = ContestRules(
    contest_type=ContestType.SHOWDOWN,
    salary_cap=50_000,
    slots=("CPT", "FLEX", "FLEX", "FLEX", "FLEX", "FLEX"),
    captain_slot="CPT",
    captain_multiplier=1.5,
    min_players_per_team=1,
)

_RULES = {ContestType.SHOWDOWN: SHOWDOWN}


class UnsupportedContest(Exception):
    pass


def get_rules(contest_type: ContestType) -> ContestRules:
    try:
        return _RULES[contest_type]
    except KeyError:
        raise UnsupportedContest(
            f"{contest_type.value} contests are not supported yet (Showdown only)."
        )