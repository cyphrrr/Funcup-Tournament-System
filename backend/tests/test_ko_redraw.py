"""
Tests für POST /seasons/{id}/ko-brackets/redraw — KO-Runde neu auslosen.

Löscht bestehende Brackets und generiert neu in einer Transaktion.
Guard: 409 wenn bereits KO-Ergebnisse eingetragen sind (außer force=true).
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi import HTTPException

from app import models, schemas
from app.routers.ko import redraw_season_ko_brackets
from test_ko_e2e import create_test_db, mock_ranking_sheet, setup_season
from app.ko_bracket_generator import generate_ko_brackets_v2


def _setup_with_bracket(db, num_groups=9):
    """Saison mit abgeschlossener Gruppenphase + generierten Brackets."""
    mock_ranking_sheet()
    season_id, group_ids, all_teams = setup_season(db, num_groups=num_groups, teams_per_group=4)
    generate_ko_brackets_v2(season_id, db)
    return season_id, group_ids, all_teams


def _r1_pairs(db, season_id):
    matches = db.query(models.KOMatch).filter(
        models.KOMatch.season_id == season_id,
        models.KOMatch.round == 1
    ).all()
    return {(m.bracket_type, m.position): (m.home_team_id, m.away_team_id) for m in matches}


def test_redraw_erzeugt_frisches_bracket():
    db = create_test_db()
    season_id, _, _ = _setup_with_bracket(db)
    old_match_count = db.query(models.KOMatch).filter(
        models.KOMatch.season_id == season_id).count()
    assert old_match_count > 0
    pairs_before = _r1_pairs(db, season_id)

    # Marker: eine Paarung manuell verfälschen — die Neuauslosung muss sie
    # durch das algorithmische Ergebnis ersetzen (beweist: Rows neu erzeugt,
    # nicht nur Ergebnisse geleert)
    m1 = db.query(models.KOMatch).filter(
        models.KOMatch.season_id == season_id,
        models.KOMatch.round == 1,
        models.KOMatch.bracket_type == "meister",
        models.KOMatch.position == 1
    ).first()
    m2 = db.query(models.KOMatch).filter(
        models.KOMatch.season_id == season_id,
        models.KOMatch.round == 1,
        models.KOMatch.bracket_type == "meister",
        models.KOMatch.position == 2
    ).first()
    m1.away_team_id, m2.away_team_id = m2.away_team_id, m1.away_team_id
    db.commit()

    result = redraw_season_ko_brackets(season_id, payload=None, db=db)

    assert result["meister"]["teams_count"] == 16
    assert db.query(models.KOMatch).filter(
        models.KOMatch.season_id == season_id).count() == old_match_count
    # Manuelle Verfälschung wurde durch die deterministische Auslosung ersetzt
    assert _r1_pairs(db, season_id) == pairs_before

    # Keine Same-Group-Paarung in Runde 1
    team_groups = {st.team_id: st.group_id for st in db.query(models.SeasonTeam).filter(
        models.SeasonTeam.season_id == season_id).all()}
    for (bt, pos), (h, a) in _r1_pairs(db, season_id).items():
        assert team_groups[h] != team_groups[a], f"Same-Group in {bt} pos {pos}"


def test_redraw_409_bei_eingetragenen_ergebnissen():
    db = create_test_db()
    season_id, _, _ = _setup_with_bracket(db)
    match = db.query(models.KOMatch).filter(
        models.KOMatch.season_id == season_id,
        models.KOMatch.round == 1
    ).first()
    match.home_goals, match.away_goals, match.status = 2, 1, "played"
    db.commit()
    pairs_before = _r1_pairs(db, season_id)

    with pytest.raises(HTTPException) as exc:
        redraw_season_ko_brackets(season_id, payload=None, db=db)

    assert exc.value.status_code == 409
    assert exc.value.detail["error"] == "results_exist"
    assert exc.value.detail["played_matches"] == 1
    # Bracket unverändert
    assert _r1_pairs(db, season_id) == pairs_before


def test_redraw_force_ueberschreibt_ergebnisse():
    db = create_test_db()
    season_id, _, _ = _setup_with_bracket(db)
    match = db.query(models.KOMatch).filter(
        models.KOMatch.season_id == season_id,
        models.KOMatch.round == 1
    ).first()
    match.home_goals, match.away_goals, match.status = 2, 1, "played"
    db.commit()

    result = redraw_season_ko_brackets(
        season_id, payload=schemas.KORedrawRequest(force=True), db=db)

    assert result["meister"]["teams_count"] == 16
    played = db.query(models.KOMatch).filter(
        models.KOMatch.season_id == season_id,
        models.KOMatch.status == "played"
    ).count()
    assert played == 0


def test_redraw_404_unbekannte_saison():
    db = create_test_db()
    with pytest.raises(HTTPException) as exc:
        redraw_season_ko_brackets(99999, payload=None, db=db)
    assert exc.value.status_code == 404


def test_redraw_400_archivierte_saison():
    db = create_test_db()
    season_id, _, _ = _setup_with_bracket(db)
    db.get(models.Season, season_id).status = "archived"
    db.commit()

    with pytest.raises(HTTPException) as exc:
        redraw_season_ko_brackets(season_id, payload=None, db=db)
    assert exc.value.status_code == 400


def test_redraw_atomar_bei_fehlgeschlagener_generierung():
    """Schlägt die Neugenerierung fehl, bleibt das alte Bracket bestehen."""
    db = create_test_db()
    season_id, group_ids, _ = _setup_with_bracket(db)
    pairs_before = _r1_pairs(db, season_id)

    # Gruppenphase nachträglich "unvollständig" machen → generate wirft ValueError
    group_match = db.query(models.Match).filter(
        models.Match.group_id == group_ids[0]
    ).first()
    group_match.status = "scheduled"
    db.commit()

    with pytest.raises(HTTPException) as exc:
        redraw_season_ko_brackets(season_id, payload=None, db=db)

    assert exc.value.status_code == 400
    # Altes Bracket unangetastet
    assert _r1_pairs(db, season_id) == pairs_before
