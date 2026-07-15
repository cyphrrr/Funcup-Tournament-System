"""
Tests für PATCH /api/teams/{id} (update_team), Fokus: logo_url löschen.

Funktioniert gegen In-Memory SQLite DB (kein laufender Server nötig).
Testet die Kernlogik update_team direkt.

Regression: Ein per URL verlinktes Wappen (Team.logo_url) ließ sich über das
Admin-Panel nicht entfernen. Das Frontend sendet beim Leeren `logo_url: null`,
der Endpoint prüfte aber `if update.logo_url is not None:` und ignorierte damit
jedes Löschen. Der Link blieb dauerhaft in der DB.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models, schemas
from app.routers.teams import update_team


def create_test_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def make_team(db, name="VFB Münster", logo_url="https://biw-pokal.de/wappen.png"):
    team = models.Team(name=name, logo_url=logo_url)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def test_clear_logo_url_with_null_removes_it():
    """Frontend sendet beim Leeren `logo_url: null` -> muss entfernt werden."""
    db = create_test_db()
    team = make_team(db, logo_url="https://biw-pokal.de/wappen.png")

    update = schemas.TeamUpdate(name="VFB Münster", logo_url=None, onlineliga_url=None)
    result = update_team(team.id, update, db=db, _="admin")

    assert result.logo_url is None


def test_clear_logo_url_with_empty_string_removes_it():
    """Leerer String muss ebenfalls zu None normalisiert werden (crests-Filter)."""
    db = create_test_db()
    team = make_team(db, logo_url="https://biw-pokal.de/wappen.png")

    update = schemas.TeamUpdate(name="VFB Münster", logo_url="", onlineliga_url=None)
    result = update_team(team.id, update, db=db, _="admin")

    assert result.logo_url is None


def test_omitting_logo_url_preserves_it():
    """Partielles Update ohne logo_url darf das Wappen nicht löschen."""
    db = create_test_db()
    team = make_team(db, logo_url="https://biw-pokal.de/wappen.png")

    update = schemas.TeamUpdate(participating_next=True)
    result = update_team(team.id, update, db=db, _="admin")

    assert result.logo_url == "https://biw-pokal.de/wappen.png"


def test_set_new_logo_url_replaces_it():
    """Neuen Wert setzen muss weiterhin funktionieren."""
    db = create_test_db()
    team = make_team(db, logo_url="https://old.png")

    update = schemas.TeamUpdate(logo_url="https://new.png")
    result = update_team(team.id, update, db=db, _="admin")

    assert result.logo_url == "https://new.png"
