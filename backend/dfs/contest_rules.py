"""
DFS contest rules.

This file contains predefined contest configurations.

The optimizer reads these rules instead of hardcoding:
- salary cap
- roster slots
- captain slot
- captain multiplier
- team constraints
- lineup limits

The generic ContestRules model lives in models.py.

Adding another contest/provider should normally mean adding another
ContestRules configuration here rather than changing the optimizer.
"""

from __future__ import annotations

from .models import ContestRules, ContestType, RosterRule


# ============================================================
# DRAFTKINGS NFL SHOWDOWN
# ============================================================

SHOWDOWN = ContestRules(
    salary_cap=50_000,
    roster_size=6,

    slots=[
        RosterRule(
            slot="CPT",
            count=1,
            eligible_positions=[
                "QB",
                "RB",
                "WR",
                "TE",
                "K",
                "DST",
            ],
        ),
        RosterRule(
            slot="FLEX",
            count=5,
            eligible_positions=[
                "QB",
                "RB",
                "WR",
                "TE",
                "K",
                "DST",
            ],
        ),
    ],

    max_players_from_team=5,
    min_players_from_team=1,

    allow_duplicate_players=False,
    allow_duplicate_lineups=False,

    require_captain=True,
    captain_multiplier=1.5,

    extra_rules={
        "provider": "draftkings",
        "contest": "nfl_showdown",
        "max_lineups_per_file": 500,
    },
)


# ============================================================
# FUTURE CLASSIC CONFIGURATION
# ============================================================

# Keep this disabled until the Classic parser/optimizer is
# implemented.
#
# Example structure only:
#
# CLASSIC = ContestRules(
#     salary_cap=50_000,
#     roster_size=9,
#     slots=[
#         RosterRule(
#             slot="QB",
#             count=1,
#             eligible_positions=["QB"],
#         ),
#         RosterRule(
#             slot="RB",
#             count=2,
#             eligible_positions=["RB"],
#         ),
#         RosterRule(
#             slot="WR",
#             count=3,
#             eligible_positions=["WR"],
#         ),
#         RosterRule(
#             slot="TE",
#             count=1,
#             eligible_positions=["TE"],
#         ),
#         RosterRule(
#             slot="FLEX",
#             count=1,
#             eligible_positions=["RB", "WR", "TE"],
#         ),
#         RosterRule(
#             slot="DST",
#             count=1,
#             eligible_positions=["DST"],
#         ),
#     ],
#     max_players_from_team=None,
#     min_players_from_team=None,
#     allow_duplicate_players=False,
#     allow_duplicate_lineups=False,
#     require_captain=False,
#     captain_multiplier=None,
#     extra_rules={
#         "provider": "draftkings",
#         "contest": "nfl_classic",
#         "max_lineups_per_file": 500,
#     },
# )


# ============================================================
# RULE REGISTRY
# ============================================================

_RULES: dict[ContestType, ContestRules] = {
    ContestType.SHOWDOWN: SHOWDOWN,
}


# ============================================================
# ERRORS
# ============================================================

class UnsupportedContest(Exception):
    """Raised when no configuration exists for a contest type."""


# ============================================================
# PUBLIC API
# ============================================================

def get_rules(
    contest_type: ContestType,
) -> ContestRules:
    """
    Return the configured rules for a contest type.
    """

    try:
        return _RULES[contest_type]

    except KeyError:
        raise UnsupportedContest(
            (
                f"{contest_type.value} contests are not "
                "supported yet."
            )
        )


def is_supported_contest(
    contest_type: ContestType,
) -> bool:
    """
    Check whether the lineup engine currently supports
    the requested contest type.
    """

    return contest_type in _RULES