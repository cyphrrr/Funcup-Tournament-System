"""
Tests für Admin-Wappenverwaltung (UserProfile.crest_url).

Ansatz A: Admin kann das per-Owner hochgeladene Wappen (crest_url, das
Team.logo_url in /teams/crests überschreibt) per URL/Upload setzen und löschen.

Läuft gegen In-Memory SQLite (kein Server nötig); testet die Router-Funktionen
direkt. Datei-Uploads schreiben in ein temporäres UPLOAD_DIR (env, pro Prozess).
"""

import sys
import os
import io
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.datastructures import UploadFile, Headers
from PIL import Image

from app.db import Base
from app import models, schemas
from app.routers.teams import (
    admin_set_team_crest_url,
    admin_delete_team_crest,
    admin_upload_team_crest,
    validate_crest_url,
    get_team_crests,
)


def create_test_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def make_team(db, name="RW Ahrem", logo_url="https://biw-pokal.de/ahrem.png"):
    team = models.Team(name=name, logo_url=logo_url)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def make_profile(db, team_id, discord_id="12345", crest_url="/uploads/crests/12345.webp", is_active=True):
    p = models.UserProfile(
        discord_id=discord_id,
        discord_username="daniel_022941#0",
        team_id=team_id,
        crest_url=crest_url,
        is_active=is_active,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def make_png_upload(filename="wappen.png", content_type="image/png"):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), (0, 128, 255)).save(buf, "PNG")
    buf.seek(0)
    return UploadFile(filename=filename, file=buf, headers=Headers({"content-type": content_type}))


# ---------- Set per URL ----------

def test_set_crest_url_updates_profile():
    db = create_test_db()
    team = make_team(db)
    make_profile(db, team.id, crest_url="/uploads/crests/old.webp")

    body = schemas.AdminCrestUrlSet(crest_url="https://example.com/neu.png")
    result = admin_set_team_crest_url(team.id, body, db=db, _="admin")

    assert result.crest_url == "https://example.com/neu.png"
    p = db.query(models.UserProfile).filter_by(team_id=team.id).first()
    assert p.crest_url == "https://example.com/neu.png"


def test_set_crest_url_without_profile_400():
    db = create_test_db()
    team = make_team(db)  # kein UserProfile

    body = schemas.AdminCrestUrlSet(crest_url="https://example.com/neu.png")
    with pytest.raises(HTTPException) as exc:
        admin_set_team_crest_url(team.id, body, db=db, _="admin")
    assert exc.value.status_code == 400


@pytest.mark.parametrize("bad", [
    'https://x.com/a".png',        # Anführungszeichen -> Attribut-Ausbruch
    "https://x.com/a'.png",
    "https://x.com/<script>",
    "javascript:alert(1)",         # falsches Schema
    "ftp://x.com/a.png",
    "https://x.com/a b.png",       # Whitespace
    "  ",                          # leer
])
def test_set_crest_url_rejects_unsafe(bad):
    db = create_test_db()
    team = make_team(db)
    make_profile(db, team.id)

    body = schemas.AdminCrestUrlSet(crest_url=bad)
    with pytest.raises(HTTPException) as exc:
        admin_set_team_crest_url(team.id, body, db=db, _="admin")
    assert exc.value.status_code == 400


@pytest.mark.parametrize("ok", [
    "https://biw-pokal.de/wappen.png",
    "http://example.com/x.webp",
    "/uploads/crests/12345.webp",
])
def test_validate_crest_url_accepts_valid(ok):
    validate_crest_url(ok)  # darf nicht werfen


# ---------- Delete ----------

def test_delete_crest_falls_back_to_logo_url():
    db = create_test_db()
    team = make_team(db, logo_url="https://biw-pokal.de/ahrem.png")
    make_profile(db, team.id, crest_url="https://example.com/falsch.png")

    result = admin_delete_team_crest(team.id, db=db, _="admin")
    assert result.crest_url is None

    crests = get_team_crests(db=db)
    # /teams/crests fällt jetzt auf Team.logo_url zurück
    assert crests[str(team.id)] == "https://biw-pokal.de/ahrem.png"


def test_delete_crest_without_any_404():
    db = create_test_db()
    team = make_team(db)
    make_profile(db, team.id, crest_url=None)

    with pytest.raises(HTTPException) as exc:
        admin_delete_team_crest(team.id, db=db, _="admin")
    assert exc.value.status_code == 404


# ---------- Upload ----------

def test_upload_crest_sets_versioned_url_and_writes_file(tmp_path):
    os.environ["UPLOAD_DIR"] = str(tmp_path)
    db = create_test_db()
    team = make_team(db)
    make_profile(db, team.id, discord_id="999", crest_url=None)

    upload = make_png_upload()
    result = asyncio.run(admin_upload_team_crest(team.id, upload, db=db, _="admin"))

    assert result.crest_url.startswith("/uploads/crests/999.webp?v=")
    written = tmp_path / "crests" / "999.webp"
    assert written.exists() and written.stat().st_size > 0

    p = db.query(models.UserProfile).filter_by(team_id=team.id).first()
    assert p.crest_url == result.crest_url


def test_upload_crest_without_profile_400(tmp_path):
    os.environ["UPLOAD_DIR"] = str(tmp_path)
    db = create_test_db()
    team = make_team(db)  # kein Profil

    upload = make_png_upload()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(admin_upload_team_crest(team.id, upload, db=db, _="admin"))
    assert exc.value.status_code == 400
