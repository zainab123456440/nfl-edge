"""Name normalization shared by the player builder and the player matcher."""
from __future__ import annotations

import re
import unicodedata

_SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def normalize_name(name: str) -> str:
    """'Harold Fannin Jr.' -> 'harold fannin'; 'A.J. Brown' -> 'aj brown'."""
    s = unicodedata.normalize("NFKD", name)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = s.replace("'", "").replace("\u2019", "").replace(".", "")
    s = re.sub(r"[-,]", " ", s)
    s = re.sub(r"[^a-z0-9 ]", "", s)
    parts = s.split()
    while len(parts) > 1 and parts[-1] in _SUFFIXES:
        parts.pop()
    return " ".join(parts)


def make_player_key(name: str, team: str) -> str:
    return f"{normalize_name(name)}|{team.strip().upper()}"