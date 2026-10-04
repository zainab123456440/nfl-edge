
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client


# ============================================================
# CONFIG
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent

# .env:
# C:\Projects\NFL-EDGE\backend\.env
ENV_FILE = SCRIPT_DIR / ".env"

# Output:
# C:\Projects\NFL-EDGE\NFL_Week_4.txt
OUTPUT_FILE = SCRIPT_DIR.parent / "NFL_Week_4.txt"

BATCH_SIZE = 1000

SEASON = 2026
WEEK = 4


# ============================================================
# LOAD ENVIRONMENT
# ============================================================

if not ENV_FILE.exists():
    raise RuntimeError(
        f".env file not found at:\n{ENV_FILE}"
    )

load_dotenv(
    ENV_FILE,
    override=True
)

SUPABASE_URL = os.getenv("SUPABASE_URL")

SUPABASE_SERVICE_ROLE_KEY = os.getenv(
    "SUPABASE_SERVICE_ROLE_KEY"
)

if not SUPABASE_URL:
    raise RuntimeError(
        f"SUPABASE_URL not found in:\n{ENV_FILE}"
    )

if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError(
        f"SUPABASE_SERVICE_ROLE_KEY not found in:\n{ENV_FILE}"
    )


# ============================================================
# SUPABASE CLIENT
# ============================================================

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY
)


# ============================================================
# PAGINATED FETCH
# ============================================================

def fetch_all(query_builder, label):
    """
    Fetch all rows from Supabase using pagination.
    """

    rows = []
    offset = 0

    print(f"\nFetching {label}...")

    while True:

        response = (
            query_builder
            .range(
                offset,
                offset + BATCH_SIZE - 1
            )
            .execute()
        )

        batch = response.data or []

        if not batch:
            break

        rows.extend(batch)

        print(
            f"  {len(rows):,} records loaded",
            end="\r",
            flush=True
        )

        if len(batch) < BATCH_SIZE:
            break

        offset += BATCH_SIZE

    print(
        f"  {label}: {len(rows):,} records"
    )

    return rows


# ============================================================
# WEEK 4 GAMES
# ============================================================

def fetch_games():

    return fetch_all(
        supabase
        .table("games")
        .select("*")
        .eq("season", SEASON)
        .eq("week", WEEK)
        .order("kickoff_at"),
        "Week 4 games"
    )


# ============================================================
# GAME IDS
# ============================================================

def get_game_ids(games):

    return [
        game["id"]
        for game in games
        if game.get("id") is not None
    ]


# ============================================================
# PROPS CURRENT
# ============================================================

def fetch_props_current(game_ids):

    if not game_ids:
        return []

    rows = []

    print("\nFetching props_current...")

    GAME_ID_BATCH = 50

    for start in range(
        0,
        len(game_ids),
        GAME_ID_BATCH
    ):

        ids = game_ids[
            start:start + GAME_ID_BATCH
        ]

        offset = 0

        while True:

            response = (
                supabase
                .table("props_current")
                .select("*")
                .in_("game_id", ids)
                .range(
                    offset,
                    offset + BATCH_SIZE - 1
                )
                .execute()
            )

            batch = response.data or []

            if not batch:
                break

            rows.extend(batch)

            print(
                f"  {len(rows):,} records loaded",
                end="\r",
                flush=True
            )

            if len(batch) < BATCH_SIZE:
                break

            offset += BATCH_SIZE

    print(
        f"  props_current: {len(rows):,} records"
    )

    return rows


# ============================================================
# PROPS HISTORY
# ============================================================

def fetch_props_history(game_ids):

    if not game_ids:
        return []

    rows = []

    print("\nFetching props_history...")

    GAME_ID_BATCH = 25

    for start in range(
        0,
        len(game_ids),
        GAME_ID_BATCH
    ):

        ids = game_ids[
            start:start + GAME_ID_BATCH
        ]

        offset = 0

        while True:

            response = (
                supabase
                .table("props_history")
                .select("*")
                .in_("game_id", ids)
                .range(
                    offset,
                    offset + BATCH_SIZE - 1
                )
                .execute()
            )

            batch = response.data or []

            if not batch:
                break

            rows.extend(batch)

            print(
                f"  {len(rows):,} records loaded",
                end="\r",
                flush=True
            )

            if len(batch) < BATCH_SIZE:
                break

            offset += BATCH_SIZE

    print(
        f"  props_history: {len(rows):,} records"
    )

    return rows


# ============================================================
# ODDS SNAPSHOTS
# ============================================================

def fetch_odds_snapshots(game_ids):

    if not game_ids:
        return []

    rows = []

    print("\nFetching odds_snapshots...")

    GAME_ID_BATCH = 50

    for start in range(
        0,
        len(game_ids),
        GAME_ID_BATCH
    ):

        ids = game_ids[
            start:start + GAME_ID_BATCH
        ]

        offset = 0

        while True:

            response = (
                supabase
                .table("odds_snapshots")
                .select("*")
                .in_("game_id", ids)
                .range(
                    offset,
                    offset + BATCH_SIZE - 1
                )
                .execute()
            )

            batch = response.data or []

            if not batch:
                break

            rows.extend(batch)

            print(
                f"  {len(rows):,} records loaded",
                end="\r",
                flush=True
            )

            if len(batch) < BATCH_SIZE:
                break

            offset += BATCH_SIZE

    print(
        f"  odds_snapshots: {len(rows):,} records"
    )

    return rows


# ============================================================
# INJURIES
# ============================================================

def fetch_injuries(games):

    if not games:
        return []

    kickoff_times = [
        game["kickoff_at"]
        for game in games
        if game.get("kickoff_at")
    ]

    if not kickoff_times:
        return []

    min_kickoff = min(kickoff_times)
    max_kickoff = max(kickoff_times)

    return fetch_all(
        supabase
        .table("injuries")
        .select("*")
        .gte(
            "captured_at",
            min_kickoff
        )
        .lte(
            "captured_at",
            max_kickoff
        )
        .order("captured_at"),
        "Week 4 injuries"
    )


# ============================================================
# PLAYERS
# ============================================================

def fetch_players():

    return fetch_all(
        supabase
        .table("players")
        .select("*")
        .order("team_id")
        .order("name"),
        "players"
    )


# ============================================================
# TEAMS
# ============================================================

def fetch_teams():

    return fetch_all(
        supabase
        .table("teams")
        .select("*")
        .order("id"),
        "teams"
    )


# ============================================================
# BOOKMAKERS
# ============================================================

def fetch_bookmakers():

    return fetch_all(
        supabase
        .table("bookmakers")
        .select("*")
        .order("id"),
        "bookmakers"
    )


# ============================================================
# PROP MARKETS
# ============================================================

def fetch_prop_markets():

    return fetch_all(
        supabase
        .table("prop_markets")
        .select("*")
        .order("sort_order")
        .order("key"),
        "prop_markets"
    )


# ============================================================
# WRITE JSONL INTO TXT
# ============================================================

def write_jsonl(
    output_file,
    datasets
):

    print("\nWriting JSONL into TXT...")

    total_records = 0

    with open(
        output_file,
        "w",
        encoding="utf-8",
        newline="\n"
    ) as file:

        for table_name, records in datasets:

            for record in records:

                export_record = {
                    "table": table_name,
                    "data": record
                }

                file.write(
                    json.dumps(
                        export_record,
                        ensure_ascii=False,
                        separators=(
                            ",",
                            ":"
                        )
                    )
                    + "\n"
                )

                total_records += 1

    return total_records


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("NFL EDGE - WEEK 4 JSONL DATABASE EXPORT")
    print("=" * 65)

    print(
        f"\nSeason: {SEASON}"
    )

    print(
        f"Week:   {WEEK}"
    )

    print(
        f"ENV:    {ENV_FILE}"
    )

    print(
        f"Output: {OUTPUT_FILE}"
    )

    # --------------------------------------------------------
    # Games
    # --------------------------------------------------------

    games = fetch_games()

    if not games:

        raise RuntimeError(
            "No Week 4 games were found."
        )

    # Make sure we really got all 16 games
    print(
        f"\nWeek 4 games found: "
        f"{len(games)}"
    )

    if len(games) != 16:

        print(
            "\nWARNING:"
        )

        print(
            f"Expected 16 games, "
            f"but found {len(games)}."
        )

        print(
            "The export will continue with "
            "the games currently in the database."
        )

    game_ids = get_game_ids(
        games
    )

    print(
        f"Game IDs found: "
        f"{len(game_ids)}"
    )

    # --------------------------------------------------------
    # Game-related data
    # --------------------------------------------------------

    props_current = fetch_props_current(
        game_ids
    )

    props_history = fetch_props_history(
        game_ids
    )

    odds_snapshots = fetch_odds_snapshots(
        game_ids
    )

    injuries = fetch_injuries(
        games
    )

    # --------------------------------------------------------
    # Reference data
    # --------------------------------------------------------

    players = fetch_players()

    teams = fetch_teams()

    bookmakers = fetch_bookmakers()

    prop_markets = fetch_prop_markets()

    # --------------------------------------------------------
    # Dataset collection
    # --------------------------------------------------------

    datasets = [

        (
            "games",
            games
        ),

        (
            "props_current",
            props_current
        ),

        (
            "props_history",
            props_history
        ),

        (
            "odds_snapshots",
            odds_snapshots
        ),

        (
            "injuries",
            injuries
        ),

        (
            "players",
            players
        ),

        (
            "teams",
            teams
        ),

        (
            "bookmakers",
            bookmakers
        ),

        (
            "prop_markets",
            prop_markets
        ),
    ]

    # --------------------------------------------------------
    # Write file
    # --------------------------------------------------------

    total_records = write_jsonl(
        OUTPUT_FILE,
        datasets
    )

    # --------------------------------------------------------
    # File size
    # --------------------------------------------------------

    file_size_mb = (
        OUTPUT_FILE.stat().st_size
        / (1024 * 1024)
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print(
        "\n" + "=" * 65
    )

    print(
        "WEEK 4 EXPORT COMPLETE"
    )

    print(
        "=" * 65
    )

    print(
        f"\nOutput:"
        f"\n  {OUTPUT_FILE}"
    )

    print(
        f"\nFile size:"
        f"\n  {file_size_mb:.2f} MB"
    )

    print(
        "\nRecords exported:"
    )

    for table_name, records in datasets:

        print(
            f"  {table_name:<18}"
            f"{len(records):,}"
        )

    print(
        f"\nTotal JSONL records:"
        f" {total_records:,}"
    )

    print(
        "\nFormat:"
        "\n  TXT file"
        "\n  JSONL content"
        "\n  One JSON object per line"
    )

    print(
        "\nDone."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()