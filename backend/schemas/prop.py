from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel


class PropMarket(BaseModel):
    key: str
    label: str
    position_group: Optional[str] = None


class PropOut(BaseModel):
    """One book's current line for a player/market/game."""
    id: int
    game_id: int
    player_id: int
    player_name: Optional[str] = None
    position: Optional[str] = None
    team_id: Optional[int] = None
    market: str
    bookmaker_id: int
    bookmaker: Optional[str] = None
    line: Optional[float] = None
    over_odds: Optional[int] = None
    under_odds: Optional[int] = None
    opening_line: Optional[float] = None
    line_movement: Optional[float] = None
    updated_at: Optional[datetime] = None
    injury_status: Optional[str] = None


class PropListResponse(BaseModel):
    count: int
    data: List[PropOut]


class PropHistoryPoint(BaseModel):
    bookmaker_id: int
    line: Optional[float] = None
    over_odds: Optional[int] = None
    under_odds: Optional[int] = None
    recorded_at: datetime


class PropHistoryResponse(BaseModel):
    game_id: int
    player_id: int
    market: str
    points: List[PropHistoryPoint]


# ---- Saved props ----
class SavedPropCreate(BaseModel):
    player_id: int
    game_id: int
    market: str
    line_at_save: Optional[float] = None
    side: Optional[Literal["over", "under"]] = None


class SavedPropOut(SavedPropCreate):
    id: int
    created_at: datetime


# ---- Alerts ----
AlertCondition = Literal["line_moves", "odds_above", "odds_below"]


class AlertCreate(BaseModel):
    player_id: int
    market: str
    condition: AlertCondition
    target_value: Optional[float] = None
    game_id: Optional[int] = None
    bookmaker_id: Optional[int] = None


class AlertOut(AlertCreate):
    id: int
    is_active: bool
    last_triggered_at: Optional[datetime] = None
    created_at: datetime