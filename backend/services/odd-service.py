import httpx
from config import settings

async def fetch_live_odds():
    if not settings.THE_ODDS_API_KEY:
        return {"error": "API key missing", "data": None}

    url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds/"
    params = {
        "apiKey": settings.THE_ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return {"error": None, "data": response.json()}
        except httpx.HTTPError as e:
            print(f"Odds API Error: {e}")
            return {"error": str(e), "data": None}