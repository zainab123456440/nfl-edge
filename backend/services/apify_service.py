import httpx
from config import settings

async def fetch_apify_injuries(actor_id: str = "neverempty~sports-mcp-server"):
    if not settings.APIFY_API_TOKEN:
        return {"error": "API key missing", "data": None}

    # Endpoint to run an Apify actor and wait for the dataset
    url = f"https://api.apify.com/v2/acts/{actor_id}/run-sync-get-dataset-items"
    params = {
        "token": settings.APIFY_API_TOKEN
    }
    # Payload depends on the specific actor's input schema
    payload = {
        "sport": "nfl",
        "type": "injuries"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(url, params=params, json=payload)
            response.raise_for_status()
            return {"error": None, "data": response.json()}
        except httpx.HTTPError as e:
            print(f"Apify Error: {e}")
            return {"error": str(e), "data": None}