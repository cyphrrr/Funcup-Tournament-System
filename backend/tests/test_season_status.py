"""
Tests für Saison-Status-Übergänge (PATCH /api/seasons/{id}).

Funktioniert gegen In-Memory SQLite DB (kein laufender Server nötig).
Testet die Kernlogik update_season direkt.

Regression: Archivieren einer aktiven Saison schlug fehl, weil das Frontend
immer den Namen mitschickt und der Namens-Guard den bereits mutierten Status
prüfte ("Archivierte Saisons können nicht bearbeitet werden").
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models, schemas
from app.routers.seasons import update_season


def create_test_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def make_season(db, status="active", name="Saison 51"):
    season = models.Season(name=name, participant_count=8, status=status)
    db.add(season)
    db.commit()
    db.refresh(season)
    return season


def test_archive_active_season_with_name_succeeds():
    """Frontend schickt beim Archivieren Name + status='archived' zusammen."""
    db = create_test_db()
    season = make_season(db, status="active", name="Saison 51")

    update = schemas.SeasonUpdate(name="Saison 51", status="archived", sheet_tab_gid=None)
    result = update_season(season.id, update, db=db, _="admin")

    assert result.status == "archived"
    assert result.name == "Saison 51"


def test_archive_active_season_without_name_succeeds():
    """Status-only Archivierung muss ebenfalls funktionieren."""
    db = create_test_db()
    season = make_season(db, status="active")

    update = schemas.SeasonUpdate(status="archived")
    result = update_season(season.id, update, db=db, _="admin")

    assert result.status == "archived"


def test_reactivate_archived_season_with_name_succeeds():
    """Korrektur-Übergang archived -> active mit Namen erlaubt (Reaktivierung)."""
    db = create_test_db()
    season = make_season(db, status="archived", name="Saison 50")

    update = schemas.SeasonUpdate(name="Saison 50 neu", status="active", sheet_tab_gid=None)
    result = update_season(season.id, update, db=db, _="admin")

    assert result.status == "active"
    assert result.name == "Saison 50 neu"


def test_edit_archived_season_name_only_still_blocked():
    """Reine Namensänderung einer archivierten Saison bleibt verboten."""
    db = create_test_db()
    season = make_season(db, status="archived", name="Saison 50")

    update = schemas.SeasonUpdate(name="Hacked")
    try:
        update_season(season.id, update, db=db, _="admin")
        assert False, "Erwartete HTTPException 400"
    except HTTPException as e:
        assert e.status_code == 400


def test_invalid_transition_rejected():
    """active -> planned ist kein gültiger Übergang."""
    db = create_test_db()
    season = make_season(db, status="active")

    update = schemas.SeasonUpdate(status="planned")
    try:
        update_season(season.id, update, db=db, _="admin")
        assert False, "Erwartete HTTPException 400"
    except HTTPException as e:
        assert e.status_code == 400


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
