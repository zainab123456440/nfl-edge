from enum import Enum
from datetime import datetime
from pydantic import BaseModel

class DataSourceStatus(str, Enum):
    LIVE = "live"
    DEMO = "demo"
    UNAVAILABLE = "unavailable"

class DataSourcesMeta(BaseModel):
    nfl_games: DataSourceStatus
    odds: DataSourceStatus
    injuries: DataSourceStatus
    ai_analysis: DataSourceStatus
    last_updated: datetime