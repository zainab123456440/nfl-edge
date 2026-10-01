from pathlib import Path
from unittest import TestCase

from dfs.contest_rules import SHOWDOWN
from dfs.dk_parser import DKParseError, parse_dk_csv
from dfs.names import make_player_key, normalize_name
from dfs.player_builder import load_slate
from dfs.models import ContestType

FIXTURE = Path(__file__).parent / "fixtures" / "DKSalaries_5_.csv"


def load_test_slate():
    return load_slate(FIXTURE.read_bytes())


def test_finds_header_and_rows():
    template, rows = parse_dk_csv(FIXTURE.read_bytes())
    assert template == ["CPT", "FLEX", "FLEX", "FLEX", "FLEX", "FLEX"]
    assert len(rows) == 102


def test_showdown_detected():
    slate = load_test_slate()
    assert slate.contest_type == ContestType.SHOWDOWN
    assert slate.slots == list(SHOWDOWN.slots)


def test_exactly_51_players():
    slate = load_test_slate()
    assert len(slate.players) == 51
    assert len({p.player_key for p in slate.players}) == 51


def test_ids_unique_and_distinct_per_slot():
    slate = load_test_slate()
    ids = [p.flex_id for p in slate.players] + [p.cpt_id for p in slate.players]
    assert len(ids) == len(set(ids)) == 102


def test_cpt_salary_is_1_5x():
    slate = load_test_slate()
    assert all(p.cpt_salary == round(p.flex_salary * 1.5) for p in slate.players)


def test_no_warnings():
    slate = load_test_slate()
    assert slate.warnings == []


def test_game_info_and_timezone():
    slate = load_test_slate()
    g = slate.game
    assert (g.away_team, g.home_team) == ("PIT", "CLE")
    # 8:15 PM ET on 10/01/2026 (EDT, UTC-4) = 00:15 UTC on 10/02
    assert g.kickoff_utc.isoformat() == "2026-10-02T00:15:00+00:00"


def test_known_player():
    slate = load_test_slate()
    rodgers = next(p for p in slate.players if p.name == "Aaron Rodgers")
    assert (rodgers.flex_id, rodgers.cpt_id) == ("44315892", "44315943")
    assert (rodgers.flex_salary, rodgers.cpt_salary) == (9800, 14700)
    assert rodgers.team == "PIT" and rodgers.position == "QB"


def test_name_normalization():
    assert normalize_name("Harold Fannin Jr.") == "harold fannin"
    assert normalize_name("A.J. Brown") == "aj brown"
    assert normalize_name("Ja'Marr Chase") == "jamarr chase"
    assert make_player_key("DK Metcalf", "pit") == "dk metcalf|PIT"


def test_rejects_garbage():
    with TestCase().assertRaises(DKParseError):
        parse_dk_csv("a,b,c\n1,2,3\n")
    with TestCase().assertRaises(DKParseError):
        parse_dk_csv("")