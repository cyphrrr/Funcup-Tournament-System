"""
Tests für die Wappen-Backfill-Migration (crest_url -> Team.logo_url).

Einmal-Migration, idempotent: kopiert das per Discord-Owner gesetzte crest_url in
Team.logo_url (aktiver Profile-Wert gewinnt) und legt crest_url danach still.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models
from app.migrations import backfill_crest_to_logo


def setup_engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def seed(engine, team_logo, crest_url, is_active=True):
    Session = sessionmaker(bind=engine)
    db = Session()
    team = models.Team(name="RW Ahrem", logo_url=team_logo)
    db.add(team)
    db.commit()
    db.refresh(team)
    db.add(models.UserProfile(discord_id="1", team_id=team.id,
                              crest_url=crest_url, is_active=is_active))
    db.commit()
    tid = team.id
    db.close()
    return tid


def read(engine, tid):
    Session = sessionmaker(bind=engine)
    db = Session()
    team = db.get(models.Team, tid)
    profile = db.query(models.UserProfile).filter_by(team_id=tid).first()
    out = (team.logo_url, profile.crest_url)
    db.close()
    return out


def test_backfill_copies_active_crest_to_logo():
    engine = setup_engine()
    tid = seed(engine, team_logo=None, crest_url="/uploads/crests/x.webp")

    migrated = backfill_crest_to_logo(engine)

    assert migrated == 1
    logo, crest = read(engine, tid)
    assert logo == "/uploads/crests/x.webp"  # übernommen
    assert crest is None                       # stillgelegt


def test_backfill_crest_wins_over_existing_logo():
    """crest_url gewann in der Anzeige -> überschreibt vorhandene logo_url."""
    engine = setup_engine()
    tid = seed(engine, team_logo="https://alt-logo.png", crest_url="https://gewinner.png")

    backfill_crest_to_logo(engine)

    logo, crest = read(engine, tid)
    assert logo == "https://gewinner.png"
    assert crest is None


def test_backfill_ignores_inactive_but_clears_it():
    """Inaktive Profile blenden nichts ein; ihr crest_url wird trotzdem geleert."""
    engine = setup_engine()
    tid = seed(engine, team_logo="https://ahrem.png",
               crest_url="https://inaktiv.png", is_active=False)

    migrated = backfill_crest_to_logo(engine)

    assert migrated == 0
    logo, crest = read(engine, tid)
    assert logo == "https://ahrem.png"  # unverändert
    assert crest is None                 # trotzdem stillgelegt


def test_backfill_is_idempotent():
    engine = setup_engine()
    tid = seed(engine, team_logo=None, crest_url="/uploads/crests/x.webp")

    assert backfill_crest_to_logo(engine) == 1
    assert backfill_crest_to_logo(engine) == 0  # zweiter Lauf: nichts mehr zu tun
    logo, crest = read(engine, tid)
    assert logo == "/uploads/crests/x.webp"
    assert crest is None
