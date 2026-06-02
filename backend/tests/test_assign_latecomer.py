"""
End-to-End Tests für Nachzügler-Gruppenzuweisung.

Funktioniert gegen In-Memory SQLite DB (kein laufender Server nötig).
Testet die Kernlogik _assign_latecomer direkt (wirft HTTPException).

Tests:
1. test_happy_path: Gruppe mit 3 Teams + Pool-Team → 4 Teams, 6 Matches, participant_count +1
2. test_saison_gesperrt: ein Match 'played' → 409, Gruppe unverändert
3. test_gruppe_voll: 4 Teams → 409 GRUPPE_VOLL
4. test_team_nicht_im_pool: participating_next=False → 400
5. test_team_bereits_in_saison: Team schon SeasonTeam → 400
6. test_start_week_erhalt: bestehende ingame_week=39 → neuer Plan startet bei 39
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models
from app.routers.teams import _assign_latecomer
from app.routers.matches import generate_round_robin


def create_test_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def setup_season_with_group(db, teams_in_group: int, generate_schedule: bool = True,
                            start_week: int = 39, pool_team: bool = True):
    """Erstellt Saison mit einer Gruppe (teams_in_group Teams) + optional ein Pool-Team.

    Rückgabe: (season, group, pool_team_or_None)
    """
    season = models.Season(name="Test Saison", participant_count=teams_in_group, status="active")
    db.add(season)
    db.flush()

    group = models.Group(season_id=season.id, name="A", sort_order=0)
    db.add(group)
    db.flush()

    for i in range(teams_in_group):
        team = models.Team(name=f"Team_{i + 1}", participating_next=True)
        db.add(team)
        db.flush()
        db.add(models.SeasonTeam(season_id=season.id, team_id=team.id, group_id=group.id))
    db.flush()

    if generate_schedule and teams_in_group >= 2:
        generate_round_robin(db, group.id, season.id, start_week=start_week)
        db.flush()

    pool = None
    if pool_team:
        pool = models.Team(name="Nachzuegler", participating_next=True)
        db.add(pool)
        db.flush()

    db.commit()
    return season, group, pool


def test_happy_path():
    db = create_test_db()
    season, group, pool = setup_season_with_group(db, teams_in_group=3)

    result = _assign_latecomer(db, season.id, group.id, pool.id)

    sts = db.query(models.SeasonTeam).filter(models.SeasonTeam.group_id == group.id).all()
    assert len(sts) == 4, f"erwartet 4 Teams, ist {len(sts)}"
    assert pool.id in [st.team_id for st in sts]

    matches = db.query(models.Match).filter(models.Match.group_id == group.id).all()
    assert len(matches) == 6, f"erwartet 6 Matches, ist {len(matches)}"
    assert result["matches_created"] == 6

    db.refresh(season)
    assert season.participant_count == 4, f"erwartet 4, ist {season.participant_count}"


def test_saison_gesperrt():
    db = create_test_db()
    season, group, pool = setup_season_with_group(db, teams_in_group=3)
    m = db.query(models.Match).filter(models.Match.group_id == group.id).first()
    m.status = "played"
    db.commit()

    try:
        _assign_latecomer(db, season.id, group.id, pool.id)
        assert False, "erwartete HTTPException SAISON_GESPERRT"
    except HTTPException as e:
        assert e.status_code == 409, f"erwartet 409, ist {e.status_code}"
        assert e.detail == "SAISON_GESPERRT", f"detail={e.detail}"

    count = db.query(models.SeasonTeam).filter(models.SeasonTeam.group_id == group.id).count()
    assert count == 3, f"erwartet 3 Teams unverändert, ist {count}"


def test_gruppe_voll():
    db = create_test_db()
    season, group, pool = setup_season_with_group(db, teams_in_group=4)

    try:
        _assign_latecomer(db, season.id, group.id, pool.id)
        assert False, "erwartete HTTPException GRUPPE_VOLL"
    except HTTPException as e:
        assert e.status_code == 409, f"erwartet 409, ist {e.status_code}"
        assert e.detail == "GRUPPE_VOLL", f"detail={e.detail}"


def test_team_nicht_im_pool():
    db = create_test_db()
    season, group, pool = setup_season_with_group(db, teams_in_group=3, pool_team=False)
    fremd = models.Team(name="Fremd", participating_next=False)
    db.add(fremd)
    db.commit()

    try:
        _assign_latecomer(db, season.id, group.id, fremd.id)
        assert False, "erwartete HTTPException TEAM_UNGUELTIG"
    except HTTPException as e:
        assert e.status_code == 400, f"erwartet 400, ist {e.status_code}"
        assert e.detail == "TEAM_UNGUELTIG", f"detail={e.detail}"


def test_team_bereits_in_saison():
    db = create_test_db()
    season, group, pool = setup_season_with_group(db, teams_in_group=3)
    bestehendes_st = db.query(models.SeasonTeam).filter(
        models.SeasonTeam.group_id == group.id
    ).first()

    try:
        _assign_latecomer(db, season.id, group.id, bestehendes_st.team_id)
        assert False, "erwartete HTTPException TEAM_BEREITS_IN_SAISON"
    except HTTPException as e:
        assert e.status_code == 400, f"erwartet 400, ist {e.status_code}"
        assert e.detail == "TEAM_BEREITS_IN_SAISON", f"detail={e.detail}"


def test_start_week_erhalt():
    db = create_test_db()
    season, group, pool = setup_season_with_group(db, teams_in_group=3, start_week=39)

    _assign_latecomer(db, season.id, group.id, pool.id)

    matches = db.query(models.Match).filter(models.Match.group_id == group.id).all()
    weeks = [m.ingame_week for m in matches]
    assert min(weeks) == 39, f"erwartet Startwoche 39, ist {min(weeks)}"
    assert max(weeks) == 41, f"erwartet Endwoche 41, ist {max(weeks)}"


if __name__ == "__main__":
    print("=" * 70)
    print("NACHZÜGLER-GRUPPENZUWEISUNG — END-TO-END TESTS")
    print("=" * 70)

    tests = [
        ("test_happy_path", test_happy_path),
        ("test_saison_gesperrt", test_saison_gesperrt),
        ("test_gruppe_voll", test_gruppe_voll),
        ("test_team_nicht_im_pool", test_team_nicht_im_pool),
        ("test_team_bereits_in_saison", test_team_bereits_in_saison),
        ("test_start_week_erhalt", test_start_week_erhalt),
    ]

    failed = []
    for test_name, test_fn in tests:
        try:
            test_fn()
            print(f"✓ {test_name} bestanden")
        except AssertionError as e:
            print(f"✗ {test_name}: {e}")
            failed.append(test_name)
        except Exception as e:
            import traceback
            print(f"✗ {test_name}: EXCEPTION")
            traceback.print_exc()
            failed.append(test_name)

    print("\n" + "=" * 70)
    if failed:
        print(f"✗ {len(failed)}/{len(tests)} Test(s) fehlgeschlagen:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    print(f"✓ Alle {len(tests)} Tests bestanden!")
    print("=" * 70)
