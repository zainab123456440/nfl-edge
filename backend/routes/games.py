from fastapi import APIRouter
from typing import List
from schemas.game import GamesListResponse
from schemas.common import DataSourcesMeta, DataSourceStatus
from services.sport_services import get_nfl_games
from datetime import datetime, timezone

router = APIRouter(prefix="/api/games", tags=["Games"])

@router.get("", response_model=GamesListResponse)
async def get_games():
    raw_games = await get_nfl_games()
    
    # Determine the status based on the data source
    current_status = DataSourceStatus.DEMO
    if raw_games and raw_games[0].get("data_source") == "live":
        current_status = DataSourceStatus.LIVE

    meta = DataSourcesMeta(
        nfl_games=current_status,
        odds=current_status,
        injuries=DataSourceStatus.UNAVAILABLE,
        ai_analysis=DataSourceStatus.LIVE,
        last_updated=datetime.now(timezone.utc)
    )
    
    return GamesListResponse(data=raw_games, meta=meta)