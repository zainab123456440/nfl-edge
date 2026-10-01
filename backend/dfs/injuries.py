"""Latest injury status per player -> availability multiplier. Pure logic."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .names import make_player_key

# status keyword -> multiplier on projected points. 0.0 means exclude.
# Unknown statuses are treated as healthy (1.0) but reported as warnings.
EXCLUDE = 0.0
STATUS_MULTIPLIERS = [
    ("injured reserve", EXCLUDE), ("out", EXCLUDE), ("ir", EXCLUDE), ("pup", EXCLUDE),
    ("nfi", EXCLUDE), ("suspend", EXCLUDE), ("inactive", EXCLUDE), ("cut", EXCLUDE),
    ("doubtful", EXCLUDE),
    ("questionable", 0.90), ("day-to-day", 0.90), ("day to day", 0.90), ("limited", 0.90),
    ("cleared", 1.0), ("probable", 1.0), ("active", 1.0), ("healthy", 1.0), ("full", 1.0),
]


@dataclass(frozen=True)
class Availability:
    status: str
    multiplier: float

    @property
    def excluded(self) -> bool:
        return self.multiplier == EXCLUDE


def classify(status: str | None) -> tuple[float, bool]:
    """Returns (multiplier, recognized)."""
    s = (status or "").strip().lower()
    if not s:
        return 1.0, True
    # whole-word-ish match so 'out' does not hit 'without'
    tokens = set(s.replace("-", " ").replace("/", " ").split())
    for keyword, mult in STATUS_MULTIPLIERS:
        kw_tokens = set(keyword.replace("-", " ").split())
        if kw_tokens <= tokens or s == keyword:
            return mult, True
    return 1.0, False


def latest_availability(
    rows: list[dict], teams_by_id: dict[int, str] | None = None
) -> tuple[dict, list[str]]:
    """rows: {player_id, player_name, team_id, status, captured_at}.

    Returns ({key: Availability}, warnings). Keys are both the player_id (int)
    and the 'normalized name|TEAM' key, so either lookup works."""
    teams_by_id = teams_by_id or {}
    newest: dict[tuple, dict] = {}
    for r in rows:
        ident = r.get("player_id") or (r.get("player_name"), r.get("team_id"))
        if ident not in newest or r["captured_at"] > newest[ident]["captured_at"]:
            newest[ident] = r

    out: dict = {}
    warnings: list[str] = []
    for r in newest.values():
        mult, known = classify(r.get("status"))
        if not known:
            warnings.append(f"Unrecognized injury status {r.get('status')!r} for {r.get('player_name')}.")
        av = Availability(status=r.get("status") or "", multiplier=mult)
        if r.get("player_id"):
            out[r["player_id"]] = av
        team = teams_by_id.get(r.get("team_id"))
        if r.get("player_name") and team:
            out[make_player_key(r["player_name"], team)] = av
    return out, warnings


def availability_for(player_id: Optional[int], player_key: str, table: dict) -> Availability:
    if player_id is not None and player_id in table:
        return table[player_id]
    return table.get(player_key, Availability(status="", multiplier=1.0))