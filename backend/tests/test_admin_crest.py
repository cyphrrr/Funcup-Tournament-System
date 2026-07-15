"""
Tests für Wappen nach der Konsolidierung: einzige Quelle ist Team.logo_url.

- Admin-Upload schreibt Team.logo_url (kein UserProfile nötig, jedes Team).
- /teams/crests liefert nur noch Team.logo_url (kein crest_url-Override mehr).
- URL-Validierung (validate_crest_url) greift auch beim Setzen via update_team.

Läuft gegen In-Memory SQLite; Uploads schreiben in ein temporäres UPLOAD_DIR.
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
    admin_upload_team_crest,
    validate_crest_url,
    get_team_crests,
    update_team,
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


def make_profile(db, team_id, discord_id="12345", crest_url=None, is_active=True):
    p = models.UserProfile(
        discord_id=discord_id, discord_username="daniel#0", team_id=team_id,
        crest_url=crest_url, is_active=is_active,
    )
    db.add(p)
    db.commit()
    return p


def make_png_upload(filename="wappen.png", content_type="image/png"):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), (0, 128, 255)).save(buf, "PNG")
    buf.seek(0)
    return UploadFile(filename=filename, file=buf, headers=Headers({"content-type": content_type}))


# ---------- /teams/crests: nur noch Team.logo_url ----------

def test_crests_uses_only_logo_url():
    db = create_test_db()
    team = make_team(db, logo_url="https://biw-pokal.de/ahrem.png")
    crests = get_team_crests(db=db)
    assert crests[str(team.id)] == "https://biw-pokal.de/ahrem.png"


def test_crests_ignores_legacy_crest_url_override():
    """Ein (dormantes) UserProfile.crest_url darf das Wappen NICHT mehr beeinflussen."""
    db = create_test_db()
    team = make_team(db, logo_url="https://biw-pokal.de/ahrem.png")
    make_profile(db, team.id, crest_url="https://example.com/ALT-FALSCH.png")

    crests = get_team_crests(db=db)
    assert crests[str(team.id)] == "https://biw-pokal.de/ahrem.png"


def test_crests_omits_team_without_logo():
    db = create_test_db()
    team = make_team(db, logo_url=None)
    assert str(team.id) not in get_team_crests(db=db)


# ---------- Admin-Upload -> Team.logo_url ----------

def test_admin_upload_sets_team_logo_url(tmp_path):
    os.environ["UPLOAD_DIR"] = str(tmp_path)
    db = create_test_db()
    team = make_team(db, logo_url=None)  # ohne Discord-User

    result = asyncio.run(admin_upload_team_crest(team.id, make_png_upload(), db=db, _="admin"))

    assert result.crest_url.startswith(f"/uploads/crests/team-{team.id}.webp?v=")
    db.refresh(team)
    assert team.logo_url == result.crest_url
    assert (tmp_path / "crests" / f"team-{team.id}.webp").exists()


def test_admin_upload_missing_team_404(tmp_path):
    os.environ["UPLOAD_DIR"] = str(tmp_path)
    db = create_test_db()
    with pytest.raises(HTTPException) as exc:
        asyncio.run(admin_upload_team_crest(9999, make_png_upload(), db=db, _="admin"))
    assert exc.value.status_code == 404


# ---------- URL-Validierung beim Setzen via update_team ----------

@pytest.mark.parametrize("bad", [
    'https://x.com/a".png', "https://x.com/a'.png", "https://x.com/<script>",
    "javascript:alert(1)", "ftp://x.com/a.png", "https://x.com/a b.png",
])
def test_update_team_rejects_unsafe_logo_url(bad):
    db = create_test_db()
    team = make_team(db)
    with pytest.raises(HTTPException) as exc:
        update_team(team.id, schemas.TeamUpdate(logo_url=bad), db=db, _="admin")
    assert exc.value.status_code == 400


@pytest.mark.parametrize("ok", [
    "https://biw-pokal.de/wappen.png", "http://example.com/x.webp", "/uploads/crests/12345.webp",
])
def test_validate_crest_url_accepts_valid(ok):
    validate_crest_url(ok)  # darf nicht werfen
