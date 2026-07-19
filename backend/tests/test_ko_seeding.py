"""
Tests für Same-Group-Vermeidung in der KO-Runde-1-Auslosung.

Hintergrund (Saison 54, Juli 2026): JungeFohlen88 [E1] und FC Wissel 2020 [E2]
trafen im 1/16-Finale direkt wieder aufeinander, weil seed_teams() rein
positionell spiegelt und keine Gruppen-Trennung kennt.

Regel: Teams aus derselben Gruppe dürfen in Runde 1 nicht gegeneinander
gelost werden. Konflikte werden durch Away-Tausch mit der nächstgelegenen
Paarung gelöst (minimale Abweichung vom Seeding).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app import models
from app.ko_bracket_generator import (
    resolve_same_group_conflicts,
    seed_teams,
    generate_ko_brackets_v2,
    preview_ko_brackets,
)
from test_ko_e2e import create_test_db, mock_ranking_sheet, setup_season


def test_konflikt_wird_durch_nachbar_tausch_geloest():
    """Saison-54-Szenario: 9 Erste (Gruppen 1-9) + 7 Zweite, E2 spiegelt auf E1."""
    # team_id 11..19 = Erste der Gruppen 1..9, 2x = Zweite (Gruppe = x)
    # Pool wie in get_qualified_teams_v2: Erste in Gruppenreihenfolge,
    # dann Zweite nach WM/EM-Ranking [26, 24, 25, 28, 22, 21, 29]
    teams = [11, 12, 13, 14, 15, 16, 17, 18, 19, 26, 24, 25, 28, 22, 21, 29]
    team_groups = {tid: tid % 10 for tid in teams}

    pairs = seed_teams(teams)
    # Vorbedingung: gespiegeltes Seeding erzeugt den Konflikt 15 vs 25 (Gruppe 5)
    assert (15, 25) in pairs

    resolved = resolve_same_group_conflicts(pairs, team_groups)

    # Keine Paarung mehr mit zwei Teams derselben Gruppe
    for home, away in resolved:
        assert team_groups[home] != team_groups[away], \
            f"Same-Group-Paarung übrig: {home} vs {away}"

    # Alle Teams noch genau einmal vertreten
    flat = [t for p in resolved for t in p]
    assert sorted(flat) == sorted(teams)

    # Minimale Abweichung: genau zwei Paarungen verändert (ein Away-Tausch)
    changed = [i for i, (a, b) in enumerate(zip(pairs, resolved)) if a != b]
    assert len(changed) == 2


def test_ohne_konflikt_bleiben_paarungen_unveraendert():
    teams = [1, 2, 3, 4, 5, 6, 7, 8]
    team_groups = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 8}
    pairs = seed_teams(teams)
    assert resolve_same_group_conflicts(pairs, team_groups) == pairs


def test_unloesbarer_konflikt_bleibt_bestehen():
    """Nur eine Paarung → kein Tauschpartner → Paarung bleibt (kein Crash)."""
    pairs = [(1, 2)]
    team_groups = {1: 1, 2: 1}
    assert resolve_same_group_conflicts(pairs, team_groups) == pairs


def test_teams_ohne_gruppenzuordnung_gelten_nicht_als_konflikt():
    pairs = [(1, 2), (3, 4)]
    team_groups = {}
    assert resolve_same_group_conflicts(pairs, team_groups) == pairs


def _group_of(db, season_id):
    rows = db.query(models.SeasonTeam).filter(
        models.SeasonTeam.season_id == season_id
    ).all()
    return {st.team_id: st.group_id for st in rows}


def test_generate_keine_same_group_paarung_in_runde_1():
    """
    Saison-54-Szenario: 9 Gruppen × 4 Teams. Das gespiegelte Seeding erzeugt
    ohne Fix Same-Group-Paarungen (z.B. D1 vs D2 in der Meisterrunde).
    """
    db = create_test_db()
    mock_ranking_sheet()
    season_id, _, _ = setup_season(db, num_groups=9, teams_per_group=4)

    generate_ko_brackets_v2(season_id, db)

    team_groups = _group_of(db, season_id)
    r1 = db.query(models.KOMatch).filter(
        models.KOMatch.season_id == season_id,
        models.KOMatch.round == 1
    ).all()
    assert r1, "Keine Runde-1-Matches generiert"

    for m in r1:
        assert team_groups[m.home_team_id] != team_groups[m.away_team_id], \
            f"Same-Group-Paarung in Runde 1 ({m.bracket_type}, pos {m.position}): " \
            f"{m.home_team_id} vs {m.away_team_id}"


def test_preview_keine_same_group_paarung_in_runde_1():
    """Preview muss dieselbe Konfliktauflösung anwenden wie Generate."""
    db = create_test_db()
    mock_ranking_sheet()
    season_id, _, _ = setup_season(db, num_groups=9, teams_per_group=4)

    preview = preview_ko_brackets(season_id, db)
    team_groups = _group_of(db, season_id)

    for bracket_type in ["meister", "lucky_loser", "loser"]:
        bracket = preview.get(bracket_type)
        if not bracket:
            continue
        for pairing in bracket["pairings_r1"]:
            assert team_groups[pairing["home"]] != team_groups[pairing["away"]], \
                f"Same-Group-Paarung in Preview ({bracket_type}): {pairing}"


def test_mehrere_konflikte_werden_geloest():
    """Zwei Same-Group-Konflikte in benachbarten Paarungen."""
    pairs = [(11, 21), (12, 22), (13, 23)]  # Gruppe = letzte Ziffer... hier: alle gleich
    team_groups = {11: 1, 21: 1, 12: 2, 22: 2, 13: 3, 23: 3}

    resolved = resolve_same_group_conflicts(pairs, team_groups)

    for home, away in resolved:
        assert team_groups[home] != team_groups[away]
    flat = [t for p in resolved for t in p]
    assert sorted(flat) == sorted([11, 21, 12, 22, 13, 23])
