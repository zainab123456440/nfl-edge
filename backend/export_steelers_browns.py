import os
import json
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client


# ============================================================
# CONFIGURATION
# ============================================================

GAME_ID = 1392264

# The .env file is in the SAME folder as this script:
# C:\Projects\NFL-EDGE\backend\.env

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# Output files will also be created in the backend folder
TXT_FILE = BASE_DIR / "steelers_browns_2026-10-01.txt"
JSON_FILE = BASE_DIR / "steelers_browns_2026-10-01.json"


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

print()
print("=" * 60)
print("NFL EDGE - DATA EXPORT")
print("=" * 60)
print()

print(f"Loading environment from:")
print(ENV_FILE)
print()

if not ENV_FILE.exists():
    raise RuntimeError(
        f".env file was not found at:\n{ENV_FILE}"
    )

load_dotenv(ENV_FILE)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")


# ============================================================
# CHECK SUPABASE CREDENTIALS
# ============================================================

if not SUPABASE_URL:
    raise RuntimeError(
        "SUPABASE_URL was not found in your backend .env file.\n\n"
        f"Expected file:\n{ENV_FILE}\n\n"
        "Make sure your .env contains:\n"
        "SUPABASE_URL=..."
    )

if not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_SERVICE_ROLE_KEY was not found in your backend .env file.\n\n"
        f"Expected file:\n{ENV_FILE}\n\n"
        "Make sure your .env contains:\n"
        "SUPABASE_SERVICE_ROLE_KEY=..."
    )

print("✓ SUPABASE_URL found")
print("✓ SUPABASE_SERVICE_ROLE_KEY found")
print()


# ============================================================
# CREATE SUPABASE CLIENT
# ============================================================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# FETCH ALL ROWS
# ============================================================

def fetch_all(table, columns="*", filters=None, page_size=1000):
    """
    Fetch all rows from a Supabase table.

    Handles pagination automatically so tables with more than
    1,000 rows are fully exported.
    """

    rows = []
    start = 0

    while True:

        query = (
            supabase
            .table(table)
            .select(columns)
        )

        if filters:
            for column, value in filters.items():
                query = query.eq(column, value)

        result = (
            query
            .range(start, start + page_size - 1)
            .execute()
        )

        batch = result.data or []

        rows.extend(batch)

        if len(batch) < page_size:
            break

        start += page_size

    return rows


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("EXPORTING STEELERS VS BROWNS")
    print("=" * 60)
    print()

    print(f"Game ID: {GAME_ID}")
    print()

    # ========================================================
    # GAME
    # ========================================================

    print("Fetching game...")

    games = fetch_all(
        "games",
        filters={"id": GAME_ID}
    )

    if not games:
        raise RuntimeError(
            f"Game {GAME_ID} was not found in the games table."
        )

    game = games[0]

    print(f"✓ Game found: {game.get('id')}")
    print()


    # ========================================================
    # TEAMS
    # ========================================================

    print("Fetching teams...")

    team_ids = [
        game.get("home_team_id"),
        game.get("away_team_id")
    ]

    team_ids = [
        team_id
        for team_id in team_ids
        if team_id is not None
    ]

    teams = []

    for team_id in team_ids:

        result = (
            supabase
            .table("teams")
            .select("*")
            .eq("id", team_id)
            .execute()
        )

        teams.extend(result.data or [])

    print(f"✓ Teams: {len(teams)}")
    print()


    # ========================================================
    # CURRENT PROPS
    # ========================================================

    print("Fetching current props...")

    current_props = fetch_all(
        "props_current",
        filters={"game_id": GAME_ID}
    )

    print(f"✓ Current props: {len(current_props)}")
    print()


    # ========================================================
    # PROP HISTORY
    # ========================================================

    print("Fetching prop history...")

    prop_history = fetch_all(
        "props_history",
        filters={"game_id": GAME_ID}
    )

    print(f"✓ Prop history: {len(prop_history)}")
    print()


    # ========================================================
    # ODDS SNAPSHOTS
    # ========================================================

    print("Fetching odds snapshots...")

    odds_snapshots = fetch_all(
        "odds_snapshots",
        filters={"game_id": GAME_ID}
    )

    print(f"✓ Odds snapshots: {len(odds_snapshots)}")
    print()


    # ========================================================
    # INJURIES
    # ========================================================

    print("Fetching injuries...")

    injuries = []

    for team_id in team_ids:

        result = (
            supabase
            .table("injuries")
            .select("*")
            .eq("team_id", team_id)
            .execute()
        )

        injuries.extend(result.data or [])

    print(f"✓ Injuries: {len(injuries)}")
    print()


    # ========================================================
    # PLAYERS
    # ========================================================

    print("Fetching players...")

    player_ids = sorted(
        {
            row.get("player_id")
            for row in current_props
            if row.get("player_id") is not None
        }
    )

    players = []

    for player_id in player_ids:

        result = (
            supabase
            .table("players")
            .select("*")
            .eq("id", player_id)
            .execute()
        )

        players.extend(result.data or [])

    print(f"✓ Players: {len(players)}")
    print()


    # ========================================================
    # BOOKMAKERS
    # ========================================================

    print("Fetching bookmakers...")

    bookmaker_ids = sorted(
        {
            row.get("bookmaker_id")
            for row in current_props
            if row.get("bookmaker_id") is not None
        }
    )

    bookmakers = []

    for bookmaker_id in bookmaker_ids:

        result = (
            supabase
            .table("bookmakers")
            .select("*")
            .eq("id", bookmaker_id)
            .execute()
        )

        bookmakers.extend(result.data or [])

    print(f"✓ Bookmakers: {len(bookmakers)}")
    print()


    # ========================================================
    # BUILD JSON RECORDS
    # ========================================================

    print("Building export records...")

    records = []


    # Game
    for row in games:

        records.append({
            "type": "game",
            "data": row
        })


    # Teams
    for row in teams:

        records.append({
            "type": "team",
            "data": row
        })


    # Players
    for row in players:

        records.append({
            "type": "player",
            "data": row
        })


    # Bookmakers
    for row in bookmakers:

        records.append({
            "type": "bookmaker",
            "data": row
        })


    # Current props
    for row in current_props:

        records.append({
            "type": "player_prop",
            "data": row
        })


    # Prop history
    for row in prop_history:

        records.append({
            "type": "player_prop_history",
            "data": row
        })


    # Odds snapshots
    for row in odds_snapshots:

        records.append({
            "type": "odds_snapshot",
            "data": row
        })


    # Injuries
    for row in injuries:

        records.append({
            "type": "injury",
            "data": row
        })


    # ========================================================
    # REMOVE EXACT DUPLICATES
    # ========================================================

    unique_records = []
    seen = set()

    for record in records:

        record_key = (
            record["type"],
            json.dumps(
                record["data"],
                sort_keys=True,
                default=str
            )
        )

        if record_key not in seen:

            seen.add(record_key)
            unique_records.append(record)

    records = unique_records

    print(f"✓ Total records: {len(records)}")
    print()


    # ========================================================
    # WRITE TXT FILE - JSONL
    # ========================================================

    print("Creating TXT JSONL file...")

    with open(
        TXT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        for record in records:

            file.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                    separators=(",", ":")
                )
            )

            file.write("\n")

    print(f"✓ Created:")
    print(TXT_FILE)
    print()


    # ========================================================
    # WRITE JSON FILE
    # ========================================================

    print("Creating JSON file...")

    with open(
        JSON_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"✓ Created:")
    print(JSON_FILE)
    print()


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print("=" * 60)
    print("EXPORT COMPLETE")
    print("=" * 60)
    print()

    print(f"Total records: {len(records)}")
    print()

    print("Files:")
    print()
    print(f"TXT JSONL:")
    print(f"  {TXT_FILE}")
    print()

    print(f"Normal JSON:")
    print(f"  {JSON_FILE}")
    print()

    print("=" * 60)
    print()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()