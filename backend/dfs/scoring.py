"""DraftKings NFL scoring (full PPR). Pure functions, no I/O.

Offense values are confirmed. Kicker values are the standard Showdown values
but were NOT verified against DraftKings' rules page: check KICKER_* before
trusting kicker projections.
"""
from __future__ import annotations

# --- Offense (confirmed) -------------------------------------------------
PASS_YD, PASS_TD, INTERCEPTION = 0.04, 4.0, -1.0
RUSH_YD, RUSH_TD = 0.1, 6.0
REC_YD, REC_TD, RECEPTION = 0.1, 6.0, 1.0
FUMBLE_LOST, TWO_POINT = -1.0, 2.0
BONUS_POINTS = 3.0
BONUS_PASS_YDS, BONUS_RUSH_YDS, BONUS_REC_YDS = 300, 100, 100

# --- Kicker (VERIFY) -----------------------------------------------------
KICKER_FG_0_39, KICKER_FG_40_49, KICKER_FG_50_PLUS = 3.0, 4.0, 5.0
KICKER_XP = 1.0

# --- Team defense (points-allowed tiers, upper bound inclusive) -----------
_DST_TIERS = [(0, 10.0), (6, 7.0), (13, 4.0), (20, 1.0), (27, 0.0), (34, -1.0)]
DST_35_PLUS = -4.0
DST_SACK, DST_INT, DST_FUMBLE_REC = 1.0, 2.0, 2.0
DST_SAFETY, DST_BLOCKED_KICK, DST_RETURN_TD = 2.0, 2.0, 6.0


def offense_points(
    pass_yds=0.0, pass_tds=0.0, ints=0.0,
    rush_yds=0.0, rush_tds=0.0,
    rec=0.0, rec_yds=0.0, rec_tds=0.0,
    fumbles_lost=0.0, two_pts=0.0, apply_bonuses=True,
) -> float:
    pts = (pass_yds * PASS_YD + pass_tds * PASS_TD + ints * INTERCEPTION
           + rush_yds * RUSH_YD + rush_tds * RUSH_TD
           + rec * RECEPTION + rec_yds * REC_YD + rec_tds * REC_TD
           + fumbles_lost * FUMBLE_LOST + two_pts * TWO_POINT)
    if apply_bonuses:
        pts += BONUS_POINTS * ((pass_yds >= BONUS_PASS_YDS)
                               + (rush_yds >= BONUS_RUSH_YDS)
                               + (rec_yds >= BONUS_REC_YDS))
    return round(pts, 4)


def kicker_points(fg_0_39=0, fg_40_49=0, fg_50_plus=0, xp=0) -> float:
    return (fg_0_39 * KICKER_FG_0_39 + fg_40_49 * KICKER_FG_40_49
            + fg_50_plus * KICKER_FG_50_PLUS + xp * KICKER_XP)


def dst_points_allowed_score(points_allowed: float) -> float:
    for upper, pts in _DST_TIERS:
        if points_allowed <= upper:
            return pts
    return DST_35_PLUS


def dst_expected_points_allowed_score(implied_points_allowed: float) -> float:
    """Expected tier score when the opponent is expected to score N points.

    Points allowed is spread out, not a fixed number, so blend the tier scores
    over a rough distribution (Poisson-like on scoring drives of ~3.5 pts)
    instead of reading the tier at the mean."""
    import math
    mean_units = max(implied_points_allowed, 0.1) / 3.5
    total, exp = 0.0, 0.0
    for k in range(0, 25):
        p = math.exp(-mean_units) * mean_units ** k / math.factorial(k)
        total += p
        exp += p * dst_points_allowed_score(k * 3.5)
    return round(exp / total, 3)