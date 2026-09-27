from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from schemas.common import DataSourcesMeta, DataSourceStatus

class Team(BaseModel):
    id: str
    name: str
    abbreviation: str
    logo_url: Optional[str] = None

class MarketLine(BaseModel):
    opening: Optional[float] = None
    current: Optional[float] = None
    movement: Optional[float] = None

class Moneyline(BaseModel):
    opening: Optional[int] = None
    current: Optional[int] = None
    movement: Optional[int] = None

class GameSnapshot(BaseModel):
    id: str
    start_time: datetime
    status: str
    home_team: Team
    away_team: Team
    spread: MarketLine
    total: MarketLine
    moneyline_home: Moneyline
    moneyline_away: Moneyline
    has_significant_movement: bool
    data_source: DataSourceStatus

class GamesListResponse(BaseModel):
    data: List[GameSnapshot]
    meta: DataSourcesMeta