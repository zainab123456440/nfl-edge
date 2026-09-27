import httpx
from config import settings

async def fetch_bdl_games(date: str):
    if not settings.BALLDONTLIE_API_KEY:
        return {"error": "API key missing", "data": None}

    url = "https://api.balldontlie.io/v1/games"
    headers = {
        "Authorization": settings.BALLDONTLIE_API_KEY
    }
    params = {
        "dates[]": date
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return {"error": None, "data": response.json().get("data", [])}
        except httpx.HTTPError as e:
            print(f"BDL API Error: {e}")
            return {"error": str(e), "data": None}