"""Data models for the DFS (DraftKings) lineup engine."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ContestType(str, Enum):
    SHOWDOWN = "showdown"
    CLASSIC = "classic"


class RosterRule(BaseModel):
    """Defines one roster slot and its eligibility rules."""

    slot: str
    count: int = 1
    eligible_positions: list[str] = Field(default_factory=list)


class ContestRules(BaseModel):
    """Generic configuration for a DFS contest."""

    salary_cap: int
    roster_size: int
    slots: list[RosterRule] = Field(default_factory=list)

    max_players_from_team: Optional[int] = None
    min_players_from_team: Optional[int] = None

    allow_duplicate_players: bool = False
    allow_duplicate_lineups: bool = False

    require_captain: bool = False
    captain_multiplier: Optional[float] = None

    extra_rules: dict[str, Any] = Field(default_factory=dict)


class DKRow(BaseModel):
    """One raw data row from a DraftKings salary CSV."""

    position: str
    name_id: str
    name: str
    dk_id: str
    roster_position: str
    salary: int
    game_info: str
    team: str
    avg_points: float = 0.0


class GameInfo(BaseModel):
    raw: str
    away_team: str
    home_team: str
    kickoff_local: datetime
    kickoff_utc: datetime


class DKPlayer(BaseModel):
    """One player with CPT and FLEX DraftKings versions."""

    player_key: str
    name: str
    position: str
    team: str

    flex_id: str
    flex_salary: int

    cpt_id: str
    cpt_salary: int

    avg_points: float = 0.0

    # Filled later by player_matcher
    supabase_player_id: Optional[int] = None
    match_method: Optional[str] = None


class ParsedSlate(BaseModel):
    contest_type: ContestType
    slots: list[str]
    game: GameInfo
    players: list[DKPlayer]
    warnings: list[str] = Field(default_factory=list)