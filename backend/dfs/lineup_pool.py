"""
Generic DFS lineup engine data models.

These models are provider-agnostic and support:
- DraftKings
- FanDuel
- Other DFS providers
- Showdown contests
- Classic contests
- Future contest formats

General file handling (CSV/XLSX/TXT/JSON/PDF/etc.) should NOT live here.
This file only defines the data structures used by the DFS engine.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================
# ENUMS
# ============================================================

class ContestType(str, Enum):
    SHOWDOWN = "showdown"
    CLASSIC = "classic"
    CUSTOM = "custom"


class DFSProvider(str, Enum):
    DRAFTKINGS = "draftkings"
    FANDUEL = "fanduel"
    UNKNOWN = "unknown"


# ============================================================
# RAW SALARY / PLAYER ROWS
# ============================================================

class SalaryRow(BaseModel):
    """
    Generic normalized row from a DFS salary/contest file.

    This is provider-agnostic. Different providers can have
    different original column names; the parser should normalize
    them into this structure.
    """

    position: str = ""
    name_id: str = ""
    name: str

    dfs_id: str = ""

    roster_position: str = ""

    salary: int = 0

    game_info: str = ""

    team: str = ""

    opponent: Optional[str] = None

    avg_points: float = 0.0

    provider: DFSProvider = DFSProvider.UNKNOWN

    extra: dict[str, Any] = Field(default_factory=dict)


class DKRow(BaseModel):
    """
    Backward-compatible DraftKings salary row.

    Keep this because existing DraftKings parsing code may
    still use it.
    """

    position: str = ""
    name_id: str = ""
    name: str

    dk_id: str = ""

    roster_position: str = ""

    salary: int = 0

    game_info: str = ""

    team: str = ""

    avg_points: float = 0.0


# ============================================================
# GAME INFORMATION
# ============================================================

class GameInfo(BaseModel):
    """
    Information about the game associated with a DFS slate.
    """

    raw: str = ""

    away_team: str
    home_team: str

    kickoff_local: datetime
    kickoff_utc: datetime

    game_id: Optional[str] = None


# ============================================================
# GENERIC DFS PLAYER
# ============================================================

class DFSPlayer(BaseModel):
    """
    Provider-independent DFS player.

    A player may have different IDs, salaries, or roster
    positions depending on the DFS provider.
    """

    player_key: str

    name: str

    position: str

    team: str

    opponent: Optional[str] = None

    dfs_id: str = ""

    salary: int = 0

    roster_positions: list[str] = Field(default_factory=list)

    avg_points: float = 0.0

    provider_ids: dict[str, str] = Field(default_factory=dict)

    provider_salaries: dict[str, int] = Field(default_factory=dict)

    supabase_player_id: Optional[int] = None

    match_method: Optional[str] = None

    extra: dict[str, Any] = Field(default_factory=dict)


class DKPlayer(BaseModel):
    """
    Backward-compatible DraftKings player model.

    Supports the traditional Showdown format where a player
    has separate CPT and FLEX IDs/salaries.
    """

    player_key: str

    name: str

    position: str

    team: str

    flex_id: str

    flex_salary: int

    cpt_id: str

    cpt_salary: int

    avg_points: float = 0.0

    supabase_player_id: Optional[int] = None

    match_method: Optional[str] = None


# ============================================================
# CONTEST / ROSTER RULES
# ============================================================

class RosterRule(BaseModel):
    """
    Defines one roster slot.

    Example:

        slot="CPT"
        count=1
        eligible_positions=["QB", "RB", "WR", "TE", "K", "DST"]

    or:

        slot="FLEX"
        count=5
        eligible_positions=["QB", "RB", "WR", "TE", "K"]
    """

    slot: str

    count: int = 1

    eligible_positions: list[str] = Field(default_factory=list)


class ContestRules(BaseModel):
    """
    Defines the actual rules that the lineup engine must enforce.

    This prevents the engine from assuming that every contest is
    DraftKings Showdown.
    """

    salary_cap: int

    roster_size: int

    slots: list[RosterRule] = Field(default_factory=list)

    max_players_from_team: Optional[int] = None

    min_players_from_team: Optional[int] = None

    max_players_from_game: Optional[int] = None

    allow_duplicate_players: bool = False

    allow_duplicate_lineups: bool = False

    require_captain: bool = False

    captain_multiplier: Optional[float] = None

    extra_rules: dict[str, Any] = Field(default_factory=dict)


# ============================================================
# PARSED DFS SLATE
# ============================================================

class ParsedSlate(BaseModel):
    """
    Normalized DFS slate after the uploaded salary/contest file
    has been parsed.

    This is only used when an uploaded file is actually identified
    as DFS data.
    """

    provider: DFSProvider = DFSProvider.UNKNOWN

    contest_type: ContestType = ContestType.CUSTOM

    slots: list[str] = Field(default_factory=list)

    game: Optional[GameInfo] = None

    players: list[DFSPlayer] = Field(default_factory=list)

    rules: Optional[ContestRules] = None

    warnings: list[str] = Field(default_factory=list)

    source_filename: Optional[str] = None

    source_size_bytes: Optional[int] = None

    total_source_rows: Optional[int] = None

    parsed_rows: Optional[int] = None


# ============================================================
# GENERATED LINEUP MODELS
# ============================================================

class LineupPlayer(BaseModel):
    """
    A player occupying a specific roster slot in a generated lineup.
    """

    player_key: str

    name: str

    position: str

    team: str

    roster_position: str

    salary: int

    projected_points: float = 0.0

    dfs_id: str = ""


class Lineup(BaseModel):
    """
    One generated DFS lineup.
    """

    players: list[LineupPlayer] = Field(default_factory=list)

    total_salary: int = 0

    salary_remaining: int = 0

    projected_points: float = 0.0

    lineup_number: Optional[int] = None

    warnings: list[str] = Field(default_factory=list)


class LineupGenerationResult(BaseModel):
    """
    Final result returned by the DFS lineup engine.
    """

    provider: DFSProvider

    contest_type: ContestType

    lineups: list[Lineup] = Field(default_factory=list)

    total_generated: int = 0

    requested_count: int = 0

    warnings: list[str] = Field(default_factory=list)

    errors: list[str] = Field(default_factory=list)

    processing_time_seconds: Optional[float] = None

    source_filename: Optional[str] = None