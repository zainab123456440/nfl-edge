from pathlib import Path

import pytest

from dfs.models import DKPlayer
from dfs.player_builder import load_slate
from dfs.player_matcher import Candidate, match_players, normalize_position

FIXTURE = Path(__file__).parent / "fixtures" / "DKSalaries_5_.csv"


def dk(name, pos, team, key=None):
    from dfs.names import make_player_key
    return DKPlayer(player_key=make_player_key(name, team), name=name, position=pos, team=team,
                    flex_id="1", flex_salary=5000, cpt_id="2", cpt_salary=7500)


def run(player, cands, aliases=None):
    rep = match_players([player], cands, aliases)
    return player, rep.results[0]


def test_position_normalization():
    assert normalize_position("Quarterback") == "QB"
    assert normalize_position("Wide Receiver") == "WR"
    assert normalize_position("Tight End") == "TE"
    assert normalize_position("LB") == "LB"


def test_props_created_row_with_null_team_matches():
    p, r = run(dk("Aaron Rodgers", "QB", "PIT"), [Candidate(2, "Aaron Rodgers", "Quarterback", None, True)])
    assert r.status == "matched" and p.supabase_player_id == 2


def test_suffix_handled():
    p, r = run(dk("Harold Fannin Jr.", "TE", "CLE"), [Candidate(21, "Harold Fannin Jr.", "Tight End", None, True)])
    assert r.status == "matched" and p.supabase_player_id == 21
    p, r = run(dk("Michael Pittman Jr.", "WR", "PIT"), [Candidate(820, "Michael Pittman", "WR", "PIT")])
    assert r.status == "matched"


def test_same_name_wrong_position_is_not_matched():
    # A different Justin Jefferson (LB, CLE) must not attach to the WR.
    p, r = run(dk("Justin Jefferson", "WR", "MIN"), [Candidate(33935691, "Justin Jefferson", "LB", "CLE")])
    assert r.status == "review" and p.supabase_player_id is None


def test_team_conflict_rejected():
    p, r = run(dk("Jaylen Watson", "WR", "PIT"), [Candidate(1532, "Jaylen Watson", "WR", "LAR")])
    assert r.status == "review"


def test_duplicate_prefers_row_with_props():
    cands = [Candidate(488, "Jaylen Warren", "RB", "PIT", has_props=False),
             Candidate(7, "Jaylen Warren", "Running Back", None, has_props=True)]
    p, r = run(dk("Jaylen Warren", "RB", "PIT"), cands)
    assert r.status == "matched" and p.supabase_player_id == 7


def test_ambiguous_duplicates_flagged_not_guessed():
    cands = [Candidate(1, "Sam Jones", "WR", "PIT"), Candidate(2, "Sam Jones", "WR", "PIT")]
    p, r = run(dk("Sam Jones", "WR", "PIT"), cands)
    assert r.status == "review" and p.supabase_player_id is None


def test_initial_lastname_fallback_and_alias():
    p, r = run(dk("Michael Pittman", "WR", "PIT"), [Candidate(820, "Mike Pittman", "WR", "PIT")])
    assert r.status == "matched" and r.method == "initial_lastname"
    p, r = run(dk("Michael Pittman", "WR", "PIT"), [Candidate(820, "Jerome Pittman", "WR", "PIT")])
    assert r.status == "unmatched"  # same last name, different first initial: never guessed
    p, r = run(dk("AJ Brown", "WR", "PHI"), [Candidate(5, "A.J. Brown", "WR", "PHI")])
    assert r.status == "matched"
    p, r = run(dk("Mike Pittman", "WR", "PIT"), [Candidate(99, "Mikey Other", "WR", "PIT")],
               aliases={"mike pittman|PIT": 99})
    assert r.status == "matched" and r.method == "alias"


def test_defense_skipped_and_unknown_unmatched():
    p, r = run(dk("Steelers", "DST", "PIT"), [])
    assert r.status == "defense"
    p, r = run(dk("Nobody Atall", "WR", "PIT"), [Candidate(1, "Someone Else", "WR", "PIT")])
    assert r.status == "unmatched"


def test_inactive_candidates_ignored():
    p, r = run(dk("Aaron Rodgers", "QB", "PIT"), [Candidate(2, "Aaron Rodgers", "Quarterback", None, True, is_active=False)])
    assert r.status == "unmatched"


def test_real_file_against_sample_rows_from_your_database():
    """Candidates = the roster-sync rows and props-created rows you pasted."""
    roster = """Dillon Gabriel|QB|CLE|13873898;Dylan Sampson|RB|CLE|13874120;Joe Royer|TE|CLE|33934823;
Justin Jefferson|LB|CLE|33935691;Taylen Green|QB|CLE|33934005;Drew Allar|QB|PIT|33934017;
Eli Heidenreich|RB|PIT|33934175;Jaylen Warren|RB|PIT|488;Michael Pittman Jr.|WR|PIT|820;
Rico Dowdle|RB|PIT|520;Will Howard|QB|PIT|13873794;Cole Burgess|WR|PIT|365945;Joey Porter Jr.|CB|PIT|2636"""
    cands = []
    for item in roster.replace("\n", "").split(";"):
        n, pos, team, i = item.split("|")
        cands.append(Candidate(int(i), n, pos, team))
    cands += [Candidate(1, "Deshaun Watson", "Quarterback", None, True),
              Candidate(2, "Aaron Rodgers", "Quarterback", None, True),
              Candidate(6, "DK Metcalf", "Wide Receiver", None, True),
              Candidate(19, "Quinshon Judkins", "Running Back", None, True),
              Candidate(21, "Harold Fannin Jr.", "Tight End", None, True),
              Candidate(1532, "Jaylen Watson", "CB", "LAR"),
              Candidate(84, "Christian Watson", "Wide Receiver", None)]
    slate = load_slate(FIXTURE.read_bytes())
    rep = match_players(slate.players, cands)
    by_name = {p.name: p for p in slate.players}
    assert by_name["Aaron Rodgers"].supabase_player_id == 2
    assert by_name["Deshaun Watson"].supabase_player_id == 1
    assert by_name["DK Metcalf"].supabase_player_id == 6
    assert by_name["Harold Fannin Jr."].supabase_player_id == 21
    assert by_name["Jaylen Warren"].supabase_player_id == 488
    assert by_name["Steelers"].match_method == "defense"
    assert all(r.player_id != 33935691 for r in rep.results)  # LB Justin Jefferson never used
    print(rep.summary())


def test_fullback_in_db_matches_rb_in_dk():
    assert normalize_position("Fullback") == "FB"
    p, r = run(dk("Michael Burton", "RB", "CLE"), [Candidate(4, "Michael Burton", "Fullback", None, True)])
    assert r.status == "matched" and p.supabase_player_id == 4