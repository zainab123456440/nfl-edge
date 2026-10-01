"""Turns sportsbook prop lines into expected DraftKings fantasy points.

Pure logic: the repository passes in prop rows, the service passes in game
context and injury availability.

Method, per player and per market:
  * Count markets (receptions, pass TDs, INTs, FGs): find the Poisson mean whose
    P(over) matches the book's devigged over probability.
  * Yardage markets: assume Normal(mean, sd) with sd = a share of the line, and
    place the mean so that P(over) matches the odds (shift capped at +-15%).
  * Anytime TD: devigged probability -> expected TDs = -ln(1 - p) -> x6 points.
  * Bonus points (100 rush/rec yds, 300 pass yds) come from the same Normal.
  * Each book is converted separately, then the median across books is used.

Tiers (how much to trust a projection):
  1 = yardage/passing/kicking props available
  2 = only anytime-TD odds: salary-based baseline + TD value
  3 = team defense, or a kicker without a kicking line (from implied team totals)
  4 = no usable data: excluded unless the caller asks to include them
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import NormalDist, median
from typing import Optional

from . import scoring
from .game_context import american_to_prob
from .injuries import Availability
from .models import DKPlayer

ND = NormalDist()

# --- model constants (tunable) ----------------------------------------------
YARD_SD_SHARE = {            # sd of the stat as a share of its betting line
    "passing_yards": 0.28, "rushing_yards": 0.60, "receiving_yards": 0.60,
    "rushing_receiving_yards": 0.50, "kicking_points": 0.55,
}
MAX_SHIFT_SHARE = 0.15       # cap on how far odds can move the mean off the line
ANYTIME_TD_HOLD = 0.92       # applied when a book gives only the "yes" price
KICKER_DISTANCE_BONUS = 0.35 # extra DK points per FG for 40+ yard kicks (approximate)
KICKER_PER_IMPLIED_POINT = 0.33
DST_EVENT_BASELINE = 5.5     # sacks, turnovers, defensive TDs in an average game
LEAGUE_AVG_TEAM_TOTAL = 22.5
DEFAULT_SALARY_SLOPE = 1.0   # baseline points per $1000 for tier-2 players
SKILL = {"RB", "WR", "TE", "FB"}
POISSON_MARKETS = {"receptions", "passing_tds", "interceptions", "fg_made"}


@dataclass
class Projection:
    player_key: str
    points: float = 0.0              # FLEX-level expected points (CPT = x1.5)
    std: float = 0.0
    tier: int = 4
    excluded: bool = False
    reason: str = ""
    components: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)


# --- probability helpers -----------------------------------------------------
def devig_over(over_odds, under_odds) -> Optional[float]:
    if over_odds is None:
        return None
    po = american_to_prob(over_odds)
    if under_odds is None:
        return po
    pu = american_to_prob(under_odds)
    return po / (po + pu)


def _poisson_tail(n: int, lam: float) -> float:
    """P(N >= n) for N ~ Poisson(lam)."""
    cdf, term = 0.0, math.exp(-lam)
    for i in range(n):
        cdf += term
        term *= lam / (i + 1)
    return max(0.0, 1.0 - cdf)


def poisson_mean(line: float, p_over: Optional[float]) -> float:
    """Poisson mean such that P(N > line) = p_over (default 50%)."""
    p = 0.5 if p_over is None else min(max(p_over, 0.02), 0.98)
    n = int(math.floor(line)) + 1
    lo, hi = 0.001, 80.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if _poisson_tail(n, mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def normal_mean(line: float, p_over: Optional[float], sd_share: float) -> tuple[float, float]:
    sd = max(line * sd_share, 0.5)
    p = 0.5 if p_over is None else min(max(p_over, 0.02), 0.98)
    shift = ND.inv_cdf(p) * sd
    cap = MAX_SHIFT_SHARE * line
    return line + max(-cap, min(cap, shift)), sd


def prob_at_least(threshold: float, mean: float, sd: float) -> float:
    return 1.0 - ND.cdf((threshold - mean) / max(sd, 1e-6))


# --- per-market expected values (median across books) --------------------------
def market_stat(rows: list[dict], market: str) -> Optional[tuple[float, float]]:
    """Returns (expected value, sd) for a market, or None if no usable rows."""
    vals = []
    for r in rows:
        if r.get("line") is None:
            continue
        p_over = devig_over(r.get("over_odds"), r.get("under_odds"))
        if market in POISSON_MARKETS:
            lam = poisson_mean(float(r["line"]), p_over)
            vals.append((lam, math.sqrt(lam)))
        else:
            share = YARD_SD_SHARE.get(market, 0.5)
            vals.append(normal_mean(float(r["line"]), p_over, share))
    if not vals:
        return None
    return median(v[0] for v in vals), median(v[1] for v in vals)


def anytime_td_lambda(rows: list[dict]) -> Optional[float]:
    """Expected number of touchdowns from anytime-TD odds."""
    probs = []
    for r in rows:
        if r.get("over_odds") is None:
            continue
        # Some books store "2+ touchdowns" (line 2.0) under the same market name.
        # Only the plain "to score a TD" rows (line 0.5, or no line) count here.
        if r.get("line") is not None and float(r["line"]) > 0.5:
            continue
        if r.get("under_odds") is not None:
            p = devig_over(r["over_odds"], r["under_odds"])
        else:
            p = american_to_prob(r["over_odds"]) * ANYTIME_TD_HOLD
        probs.append(min(max(p, 0.001), 0.95))
    if not probs:
        return None
    return -math.log(1.0 - median(probs))


# --- projecting one player -----------------------------------------------------
def _bonus(mean: float, sd: float, threshold: float) -> float:
    return scoring.BONUS_POINTS * prob_at_least(threshold, mean, sd)


def _skill_yard_points(props: dict) -> tuple[dict, list]:
    """Yard/reception components for RB/WR/TE (everything except TDs)."""
    comp, notes = {}, []
    rush = market_stat(props.get("rushing_yards", []), "rushing_yards")
    rec_y = market_stat(props.get("receiving_yards", []), "receiving_yards")
    rec = market_stat(props.get("receptions", []), "receptions")
    rr = market_stat(props.get("rushing_receiving_yards", []), "rushing_receiving_yards")

    if rr and not rush and rec_y:
        rush = (max(rr[0] - rec_y[0], 0.0), rr[1])
        notes.append("rushing yards derived from rush+receiving line")
    elif rr and not rec_y and rush:
        rec_y = (max(rr[0] - rush[0], 0.0), rr[1])
        notes.append("receiving yards derived from rush+receiving line")
    elif rr and not rush and not rec_y:
        comp["rush_rec_yards"] = rr[0] * scoring.RUSH_YD
        notes.append("only a combined rush+receiving line; bonuses ignored")

    if rush:
        comp["rushing"] = rush[0] * scoring.RUSH_YD + _bonus(rush[0], rush[1], scoring.BONUS_RUSH_YDS)
    if rec_y:
        comp["receiving"] = rec_y[0] * scoring.REC_YD + _bonus(rec_y[0], rec_y[1], scoring.BONUS_REC_YDS)
    if rec:
        comp["receptions"] = rec[0] * scoring.RECEPTION
    return comp, notes


def project_player(
    player: DKPlayer,
    props: dict,                         # market -> list of rows for this player
    team_implied: Optional[float],
    opp_implied: Optional[float],
    salary_slope: float = DEFAULT_SALARY_SLOPE,
    availability: Optional[Availability] = None,
) -> Projection:
    pr = Projection(player_key=player.player_key)
    pos = player.position
    comp: dict = {}

    if pos == "DST":
        pr.tier = 3
        pa = scoring.dst_expected_points_allowed_score(opp_implied if opp_implied else LEAGUE_AVG_TEAM_TOTAL)
        comp = {"points_allowed": pa, "events": DST_EVENT_BASELINE}
        if opp_implied is None:
            pr.notes.append("no game odds: used league-average opponent total")

    elif pos == "K":
        kp = market_stat(props.get("kicking_points", []), "kicking_points")
        fg = market_stat(props.get("fg_made", []), "fg_made")
        if kp:
            pr.tier = 1
            comp["kicking"] = kp[0] + KICKER_DISTANCE_BONUS * (fg[0] if fg else kp[0] / 3.2)
        elif team_implied is not None:
            pr.tier = 3
            comp["kicking"] = KICKER_PER_IMPLIED_POINT * team_implied
            pr.notes.append("no kicking line: estimated from team implied total")
        else:
            pr.excluded, pr.reason = True, "no kicking line and no game odds"

    elif pos == "QB":
        py = market_stat(props.get("passing_yards", []), "passing_yards")
        pt = market_stat(props.get("passing_tds", []), "passing_tds")
        it = market_stat(props.get("interceptions", []), "interceptions")
        if not py and not pt:
            pr.excluded, pr.reason = True, "no passing props (likely a backup QB)"
        else:
            pr.tier = 1
            if py:
                comp["passing_yards"] = py[0] * scoring.PASS_YD + _bonus(py[0], py[1], scoring.BONUS_PASS_YDS)
            if pt:
                comp["passing_tds"] = pt[0] * scoring.PASS_TD
            if it:
                comp["interceptions"] = it[0] * scoring.INTERCEPTION
            ry = market_stat(props.get("rushing_yards", []), "rushing_yards")
            if ry:
                comp["rushing"] = ry[0] * scoring.RUSH_YD
            lam = anytime_td_lambda(props.get("anytime_td", []))
            if lam:
                comp["rushing_td"] = lam * scoring.RUSH_TD

    elif pos in SKILL:
        yard_comp, notes = _skill_yard_points(props)
        pr.notes += notes
        lam = anytime_td_lambda(props.get("anytime_td", []))
        if yard_comp:
            pr.tier = 1
            comp.update(yard_comp)
            if lam:
                comp["touchdowns"] = lam * 6.0
            else:
                pr.notes.append("no anytime-TD odds: touchdown value missing")
        elif lam:
            pr.tier = 2
            factor = 1.0
            if team_implied:
                factor = min(max(team_implied / LEAGUE_AVG_TEAM_TOTAL, 0.8), 1.2)
            comp["baseline"] = salary_slope * (player.flex_salary / 1000.0) * factor
            comp["touchdowns"] = lam * 6.0
            pr.notes.append("only TD odds: yardage estimated from salary")
        else:
            pr.excluded, pr.reason = True, "no prop data"
    else:
        pr.excluded, pr.reason = True, f"unsupported position {pos}"

    pr.components = {k: round(v, 3) for k, v in comp.items()}
    pr.points = round(sum(comp.values()), 3)

    if availability is not None and availability.multiplier != 1.0:
        pr.notes.append(f"injury status {availability.status!r}: x{availability.multiplier}")
        if availability.excluded:
            pr.excluded, pr.reason = True, f"injury status: {availability.status}"
        pr.points = round(pr.points * availability.multiplier, 3)

    spread = {1: 0.55, 2: 0.9, 3: 0.65, 4: 1.0}[pr.tier]
    pr.std = round(max(pr.points, 2.0) * spread, 3)
    return pr


# --- projecting the whole slate --------------------------------------------------
def fit_salary_slope(projections: dict, players: list[DKPlayer]) -> float:
    """Fit baseline-points-per-$1000 from tier-1 skill players (through the origin),
    excluding their TD value so tier-2 players are not double counted."""
    num = den = 0.0
    n = 0
    for p in players:
        pr = projections.get(p.player_key)
        if not pr or pr.tier != 1 or p.position not in SKILL or pr.excluded:
            continue
        y = sum(v for k, v in pr.components.items() if k != "touchdowns")
        x = p.flex_salary / 1000.0
        num += x * y
        den += x * x
        n += 1
    if n < 3 or den == 0:
        return DEFAULT_SALARY_SLOPE
    return round(min(max(num / den, 0.4), 1.8), 4)


def project_slate(
    players: list[DKPlayer],
    props_by_player: dict,                 # supabase player_id -> {market: [rows]}
    home_team: str, away_team: str,
    home_implied: Optional[float], away_implied: Optional[float],
    availability: Optional[dict] = None,   # player_key -> Availability
    include_unprojected: bool = False,
) -> tuple[dict, dict]:
    """Returns ({player_key: Projection}, info). Two passes so tier-2 players use a
    salary slope learned from this slate's tier-1 players."""
    availability = availability or {}

    def implied(team):
        own = home_implied if team == home_team else away_implied
        opp = away_implied if team == home_team else home_implied
        return own, opp

    def run(slope):
        out = {}
        for p in players:
            own, opp = implied(p.team)
            props = props_by_player.get(p.supabase_player_id, {}) if p.supabase_player_id else {}
            out[p.player_key] = project_player(p, props, own, opp, slope, availability.get(p.player_key))
        return out

    first = run(DEFAULT_SALARY_SLOPE)
    slope = fit_salary_slope(first, players)
    final = run(slope)

    if not include_unprojected:
        for pr in final.values():
            if pr.tier == 4 and not pr.excluded:
                pr.excluded, pr.reason = True, "no prop data"
    info = {
        "salary_slope_per_1000": slope,
        "tiers": {t: sum(1 for x in final.values() if x.tier == t and not x.excluded) for t in (1, 2, 3)},
        "excluded": sum(1 for x in final.values() if x.excluded),
    }
    return final, info