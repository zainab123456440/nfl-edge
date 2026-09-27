import json
import os
from config import settings
from services.odds_service import fetch_live_odds
from services.bdl_service import fetch_bdl_games
from services.apify_service import fetch_apify_injuries

async def get_nfl_games():
    """
    Orchestrates data from Apify, The Odds API, and BallDontLie.
    Falls back to demo data if keys are missing or APIs fail.
    """
    # 1. Try to fetch live data if we are in live mode
    if settings.DATA_MODE == "live" and settings.THE_ODDS_API_KEY:
        try:
            print("Attempting to fetch live market data...")
            odds_result = await fetch_live_odds()
            
            # If successful, we would map the odds_result["data"] to our GameSnapshot schema here.
            # Once you paste your actual API keys in the .env file, we will write the mapping logic!
            if not odds_result["error"]:
                pass 
                
        except Exception as e:
            print(f"Live API failed, falling back to demo. Error: {e}")

    # 2. Fallback to Demo Data (Guarantees the UI never goes blank)
    print("Using demo data fallback...")
    current_dir = os.path.dirname(os.path.realpath(__file__))
    demo_file_path = os.path.join(current_dir, "..", "data", "demo_games.json")
    
    try:
        with open(demo_file_path, "r") as f:
            demo_data = json.load(f)
            return demo_data
    except Exception as e:
        print(f"Error loading demo data: {e}")
        return []