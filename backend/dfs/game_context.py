"""Game-level context from `odds_snapshots`: total, spread, implied team totals,
win probabilities. Pure logic: the repository passes in the rows.

Row shape: {book, market ('totals'|'spreads'|'h2h'), outcome ('home'|'away'|'over'|'under'),
            line, price, captured_at}
"""
from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Optional

PREFERRED_BOOK = "draftkings"


@dataclass
class GameContext:
    total: Optional[float] = None
    home_spread: Optional[float] = None       # negative = home favored
    home_implied: Optional[float] = None
    away_implied: Optional[float] = None
    home_win_prob: Optional[float] = None
    away_win_prob: Optional[float] = None
    books_used: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def implied_for(self, team: str, home_team: str, away_team: str) -> Optional[float]:
        if team == home_team:
            return self.home_implied
        if team == away_team:
            return self.away_implied
        return None


def american_to_prob(price: float) -> float:
    return 100 / (price + 100) if price > 0 else -price / (-price + 100)


def _latest_per_book(rows: list[dict]) -> dict[tuple, dict]:
    latest: dict[tuple, dict] = {}
    for r in rows:
        k = (str(r["book"]).lower(), r["market"], r["outcome"])
        if k not in latest or r["captured_at"] > latest[k]["captured_at"]:
            latest[k] = r
    return latest


def _value(latest: dict, market: str, outcome: str, field_: str):
    """Preferred book's value, else the average across the other books."""
    pref = latest.get((PREFERRED_BOOK, market, outcome))
    if pref and pref.get(field_) is not None:
        return float(pref[field_]), PREFERRED_BOOK
    vals = [float(r[field_]) for (b, m, o), r in latest.items()
            if m == market and o == outcome and r.get(field_) is not None]
    if vals:
        return mean(vals), "average"
    return None, None


def build_game_context(rows: list[dict]) -> GameContext:
    ctx = GameContext()
    latest = _latest_per_book(rows)

    total, src = _value(latest, "totals", "over", "line")
    if total is None:
        ctx.warnings.append("No game total found.")
    ctx.total = total
    ctx.books_used["total"] = src

    spread, src = _value(latest, "spreads", "home", "line")
    if spread is None:
        away, src2 = _value(latest, "spreads", "away", "line")
        if away is not None:
            spread, src = -away, src2
    if spread is None:
        ctx.warnings.append("No spread found.")
    ctx.home_spread = spread
    ctx.books_used["spread"] = src

    if total is not None and spread is not None:
        ctx.home_implied = round(total / 2 - spread / 2, 2)
        ctx.away_implied = round(total / 2 + spread / 2, 2)

    hp, _ = _value(latest, "h2h", "home", "price")
    ap, _ = _value(latest, "h2h", "away", "price")
    if hp is not None and ap is not None:
        ph, pa = american_to_prob(hp), american_to_prob(ap)
        ctx.home_win_prob, ctx.away_win_prob = round(ph / (ph + pa), 4), round(pa / (ph + pa), 4)
    else:
        ctx.warnings.append("No moneyline found.")
    return ctx