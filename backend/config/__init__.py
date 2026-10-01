"""Settings and fixed values. No logic here."""
import os

from dotenv import load_dotenv

load_dotenv()

# --- secrets (from .env) ---
BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
CRON_SECRET = os.getenv("CRON_SECRET")
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

# --- BALLDONTLIE ---
BDL_BASE_URL = "https://api.balldontlie.io/nfl/v1"
NFL_SEASON = int(os.getenv("NFL_SEASON", "2026"))
PER_PAGE = 100  # max allowed by the API
MAX_PAGES = 50  # safety stop for cursor loops
REQUEST_TIMEOUT = 30.0

# Sportsbooks we store. Available: draftkings, fanduel, caesars, betmgm, fanatics, betrivers
BOOKS = ["draftkings", "fanduel", "betmgm", "caesars"]

# poll-odds only looks at games kicking off inside this window
ODDS_WINDOW_PAST_HOURS = 24  # keeps live games in range
ODDS_WINDOW_FUTURE_DAYS = 8  # roughly the current NFL week

DB_BATCH_SIZE = 500