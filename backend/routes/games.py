

from typing import Literal

from fastapi import APIRouter, HTTPException

from config import BOOKS, NFL_SEASON

from services import queries

router = APIRouter(prefix="/games", tags=["games"])


def _check_book(book: str | None) -> None:
    if book and book not in BOOKS:
        raise HTTPException(
            status_code=400,
            detail=f"book must be one of {BOOKS}",
        )


@router.get("")
def list_games(
    season: int = NFL_SEASON,
    week: int | None = None,  # omit -> current week
    team: str | None = None,  # name or abbreviation, e.g. "chiefs" or "KC"
    book: str | None = None,  # limit odds to one sportsbook
):
    """Games for a week, each with current odds per book and line movement."""
    _check_book(book)

    return queries.list_games(
        season=season,
        week=week,
        team=team,
        book=book,
    )


@router.get("/{game_id}")
def get_game(
    game_id: int,
):
    """One game: odds by book, opening odds, movement, and injuries for both teams."""
    game = queries.get_game_detail(game_id)

    if game is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found",
        )

    return game


@router.get("/{game_id}/line-history")
def get_line_history(
    game_id: int,
    market: Literal["spreads", "totals", "h2h"] = "spreads",
    outcome: Literal["home", "away", "over", "under"] | None = None,
    book: str | None = None,  # omit -> one series per book
):
    """Time series for the line movement chart."""
    _check_book(book)

    if outcome and outcome not in queries.VALID_OUTCOMES[market]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"outcome for '{market}' must be one of "
                f"{sorted(queries.VALID_OUTCOMES[market])}"
            ),
        )

    history = queries.get_line_history(
        game_id,
        market=market,
        outcome=outcome,
        book=book,
    )

    if history is None:
        raise HTTPException(
            status_code=404,
            detail="Game not found",
        )

    return history
