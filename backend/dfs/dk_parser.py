"""Parses a DraftKings salary CSV.

Real DK files are not plain CSVs: the first row is the upload template
(CPT,FLEX,...), instruction lines follow, and the real header sits several rows
down, shifted right by empty columns. So we locate the header row and column
offset instead of assuming row 1 / column 1.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from .models import ContestType, DKRow, GameInfo

REQUIRED_COLUMNS = [
    "Position", "Name + ID", "Name", "ID", "Roster Position",
    "Salary", "Game Info", "TeamAbbrev", "AvgPointsPerGame",
]

_ET = ZoneInfo("America/New_York")
_UTC = ZoneInfo("UTC")
_GAME_RE = re.compile(
    r"^\s*([A-Za-z]{2,4})@([A-Za-z]{2,4})\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}\s*[AaPp][Mm])"
)


class DKParseError(ValueError):
    """The file is not a valid DraftKings salary file."""


def _decode(content: bytes | str) -> str:
    if isinstance(content, str):
        return content
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    raise DKParseError("Could not read the file encoding.")


def parse_dk_csv(content: bytes | str) -> tuple[list[str], list[DKRow]]:
    """Returns (template_slots, rows). template_slots is empty if the file has no template row."""
    text = _decode(content)
    if not text.strip():
        raise DKParseError("The file is empty.")

    all_rows = list(csv.reader(io.StringIO(text)))

    header_idx = None
    for i, row in enumerate(all_rows):
        cells = [c.strip() for c in row]
        if "Position" in cells and "Salary" in cells and "Roster Position" in cells:
            header_idx = i
            break
    if header_idx is None:
        raise DKParseError(
            "This does not look like a DraftKings salary file "
            "(no header row with Position / Roster Position / Salary)."
        )

    header = [c.strip() for c in all_rows[header_idx]]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise DKParseError(f"Missing required columns: {', '.join(missing)}")
    col = {name: header.index(name) for name in REQUIRED_COLUMNS}

    # Lineup template (first row): take cells up to the first blank one.
    template: list[str] = []
    if header_idx > 0:
        for cell in all_rows[0]:
            if not cell.strip():
                break
            template.append(cell.strip().upper())

    rows: list[DKRow] = []
    max_idx = max(col.values())
    for line_no, r in enumerate(all_rows[header_idx + 1:], start=header_idx + 2):
        if len(r) <= max_idx or not r[col["ID"]].strip():
            continue  # blank or trailing row
        try:
            avg_raw = r[col["AvgPointsPerGame"]].strip()
            rows.append(DKRow(
                position=r[col["Position"]].strip().upper(),
                name_id=r[col["Name + ID"]].strip(),
                name=r[col["Name"]].strip(),
                dk_id=r[col["ID"]].strip(),
                roster_position=r[col["Roster Position"]].strip().upper(),
                salary=int(float(r[col["Salary"]])),
                game_info=r[col["Game Info"]].strip(),
                team=r[col["TeamAbbrev"]].strip().upper(),
                avg_points=float(avg_raw) if avg_raw else 0.0,
            ))
        except (ValueError, TypeError) as exc:
            raise DKParseError(f"Bad value on file line {line_no}: {exc}") from exc

    if not rows:
        raise DKParseError("No player rows found under the header.")
    return template, rows


def detect_contest_type(rows: list[DKRow]) -> ContestType:
    slots = {r.roster_position for r in rows}
    if "CPT" in slots:
        return ContestType.SHOWDOWN
    return ContestType.CLASSIC


def parse_game_info(raw: str) -> GameInfo:
    """'PIT@CLE 10/01/2026 08:15PM ET' -> teams + kickoff in ET and UTC."""
    m = _GAME_RE.match(raw)
    if not m:
        raise DKParseError(f"Could not read the game info: {raw!r}")
    away, home, date_s, time_s = m.groups()
    local = datetime.strptime(
        f"{date_s} {time_s.replace(' ', '').upper()}", "%m/%d/%Y %I:%M%p"
    ).replace(tzinfo=_ET)
    return GameInfo(
        raw=raw,
        away_team=away.upper(),
        home_team=home.upper(),
        kickoff_local=local,
        kickoff_utc=local.astimezone(_UTC),
    )