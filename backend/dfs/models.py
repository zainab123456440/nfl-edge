"""Data models for the DFS (DraftKings) lineup engine (self-contained, no outside imports)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ContestType(str, Enum):
    SHOWDOWN = "showdown"  # 1 CPT + 5 FLEX, single game
    CLASSIC = "classic"    # multi-game, positional slots (not supported yet)


class DKRow(BaseModel):
    """One raw data row from a DraftKings salary CSV."""
    position: str
    name_id: str
    name: str
    dk_id: str
    roster_position: str  # CPT / FLEX (showdown) or the slot label (classic)
    salary: int
    game_info: str
    team: str
    avg_points: float = 0.0


class GameInfo(BaseModel):
    raw: str
    away_team: str
    home_team: str
    kickoff_local: datetime  # Eastern time, tz-aware
    kickoff_utc: datetime    # tz-aware UTC (matches games.kickoff_at in Supabase)


class DKPlayer(BaseModel):
    """One player with both of his slot versions (CPT and FLEX) attached."""
    player_key: str          # normalized "name|TEAM", used to join with Supabase
    name: str
    position: str
    team: str
    flex_id: str
    flex_salary: int
    cpt_id: str
    cpt_salary: int
    avg_points: float = 0.0

    # Filled in later by player_matcher
    supabase_player_id: Optional[int] = None
    match_method: Optional[str] = None


class ParsedSlate(BaseModel):
    contest_type: ContestType
    slots: list[str]         # lineup template from the file, e.g. CPT,FLEX x5
    game: GameInfo
    players: list[DKPlayer]
    warnings: list[str] = Field(default_factory=list)