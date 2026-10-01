"""Matches DraftKings players to rows of the Supabase `players` table.

Pure logic, no database access: the repository passes in a list of Candidates.

Why this is not a simple name join (learned from the real data):
  * `players` mixes roster-sync rows (team set, positions like 'QB') with
    props-created rows (team NULL, positions like 'Quarterback'), so team_id
    cannot be required and positions must be normalized.
  * The same name can exist twice (or belong to a different player, e.g. a
    Justin Jefferson who is a linebacker), so position and team are checked
    and rows that have props for tonight's game are preferred.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .models import DKPlayer
from .names import normalize_name

_POSITION_MAP = {
    "QUARTERBACK": "QB",
    "RUNNING BACK": "RB", "HALFBACK": "RB", "HB": "RB",
    "WIDE RECEIVER": "WR",
    "TIGHT END": "TE",
    "FULLBACK": "FB",
    "KICKER": "K", "PLACE KICKER": "K", "PLACEKICKER": "K", "PK": "K",
}


def normalize_position(pos: str | None) -> str | None:
    if not pos:
        return None
    p = pos.strip().upper()
    return _POSITION_MAP.get(p, p)


def _positions_compatible(dk_pos: str, db_pos: str | None) -> bool:
    if db_pos is None:
        return True  # unknown position: cannot rule it out
    if dk_pos == db_pos:
        return True
    return {dk_pos, db_pos} == {"RB", "FB"}


@dataclass(frozen=True)
class Candidate:
    """A row from Supabase `players` that could be matched."""
    id: int
    name: str
    position: str | None = None
    team: str | None = None          # abbreviation, may be None (props-created rows)
    has_props: bool = False          # has props_current rows for tonight's game
    is_active: bool = True


@dataclass
class MatchResult:
    dk_name: str
    team: str
    position: str
    status: str                      # matched | review | unmatched | defense
    method: Optional[str] = None
    player_id: Optional[int] = None
    note: str = ""


@dataclass
class MatchReport:
    results: list[MatchResult] = field(default_factory=list)

    def _count(self, status: str) -> int:
        return sum(1 for r in self.results if r.status == status)

    @property
    def matched(self) -> int:
        return self._count("matched")

    @property
    def needs_attention(self) -> list[MatchResult]:
        return [r for r in self.results if r.status in ("review", "unmatched")]

    def summary(self) -> str:
        return (f"{self.matched} matched, {self._count('defense')} defenses, "
                f"{self._count('review')} need review, {self._count('unmatched')} unmatched "
                f"(of {len(self.results)} players)")


def _first_initial_last(norm: str) -> str:
    parts = norm.split()
    return f"{parts[0][0]} {parts[-1]}" if len(parts) >= 2 else norm


def _pick(cands: list[Candidate]) -> tuple[Optional[Candidate], str]:
    """Choose one candidate from a filtered list, or explain why we cannot."""
    if len(cands) == 1:
        return cands[0], ""
    with_props = [c for c in cands if c.has_props]
    if len(with_props) == 1:
        return with_props[0], "duplicate rows, chose the one with props for this game"
    pool = with_props or cands
    with_team = [c for c in pool if c.team]
    if len(with_team) == 1:
        return with_team[0], "duplicate rows, chose the one with a team"
    ids = ", ".join(str(c.id) for c in pool)
    return None, f"ambiguous: several players match (ids {ids})"


def match_players(
    players: list[DKPlayer],
    candidates: list[Candidate],
    aliases: dict[str, int] | None = None,
) -> MatchReport:
    """Fills supabase_player_id / match_method on each DKPlayer in place.

    aliases maps a DK player_key ('harold fannin|CLE') to a players.id and always wins.
    """
    aliases = aliases or {}
    active = [c for c in candidates if c.is_active]
    by_name: dict[str, list[Candidate]] = {}
    by_initial: dict[str, list[Candidate]] = {}
    for c in active:
        n = normalize_name(c.name)
        by_name.setdefault(n, []).append(c)
        by_initial.setdefault(_first_initial_last(n), []).append(c)
    by_id = {c.id: c for c in active}

    report = MatchReport()
    for p in players:
        res = MatchResult(dk_name=p.name, team=p.team, position=p.position, status="unmatched")
        report.results.append(res)

        if p.position == "DST":  # team defense: no player row to match
            res.status, res.method = "defense", "defense"
            p.match_method = "defense"
            continue

        # 1. manual alias
        if p.player_key in aliases and aliases[p.player_key] in by_id:
            res.status, res.method, res.player_id = "matched", "alias", aliases[p.player_key]
            p.supabase_player_id, p.match_method = res.player_id, "alias"
            continue

        norm = normalize_name(p.name)

        def usable(c: Candidate) -> bool:
            if c.team and c.team.upper() != p.team:
                return False  # team is known and conflicts with the CSV
            return _positions_compatible(p.position, normalize_position(c.position))

        # 2. exact normalized name, then 3. first initial + last name
        for method, pool in (("name", by_name.get(norm, [])),
                             ("initial_lastname", by_initial.get(_first_initial_last(norm), []))):
            same_name = list(pool)
            ok = [c for c in same_name if usable(c)]
            if not ok:
                if same_name and method == "name":
                    c = same_name[0]
                    res.status = "review"
                    res.note = (f"name found (id {c.id}, {c.position}, {c.team}) but position/team "
                                f"conflicts with CSV ({p.position}, {p.team})")
                    break
                continue
            chosen, note = _pick(ok)
            if chosen is None:
                res.status, res.note = "review", note
                break
            res.status, res.method, res.player_id, res.note = "matched", method, chosen.id, note
            p.supabase_player_id, p.match_method = chosen.id, method
            break
        else:
            res.note = "no player with this name in the database"
            continue

    return report