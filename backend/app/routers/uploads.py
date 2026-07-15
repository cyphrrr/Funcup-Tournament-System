from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..auth import get_current_user
from ..image_utils import (
    validate_image_file,
    process_crest_image,
    save_crest_webp,
    delete_crest_file,
)

router = APIRouter()


def _team_for_user(db: Session, discord_id: str) -> models.Team:
    """Liefert das mit dem eingeloggten Discord-User verknüpfte Team (oder 400/404)."""
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User-Profil nicht gefunden")
    if not user.team_id:
        raise HTTPException(
            status_code=400,
            detail="Kein Team verknüpft — Wappen gehört zu einem Team",
        )
    team = db.get(models.Team, user.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Verknüpftes Team nicht gefunden")
    return team


@router.post("/upload/crest", response_model=schemas.CrestUploadResponse)
async def upload_crest(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Wappen-Upload für den eingeloggten User → setzt Team.logo_url."""
    team = _team_for_user(db, current_user)

    file_content = await file.read()
    is_valid, error_msg = validate_image_file(
        file.filename, file.content_type, len(file_content)
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        processed_image = await process_crest_image(file_content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    delete_crest_file(team.logo_url)
    team.logo_url = await save_crest_webp(processed_image, f"team-{team.id}")
    db.commit()

    return schemas.CrestUploadResponse(
        crest_url=team.logo_url,
        message="Wappen erfolgreich hochgeladen"
    )


@router.delete("/upload/crest", response_model=schemas.CrestDeleteResponse)
async def delete_crest(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Löscht das Wappen des verknüpften Teams (Team.logo_url)."""
    team = _team_for_user(db, current_user)

    if not team.logo_url:
        raise HTTPException(status_code=404, detail="Kein Wappen vorhanden")

    delete_crest_file(team.logo_url)
    team.logo_url = None
    db.commit()

    return schemas.CrestDeleteResponse(
        message="Wappen erfolgreich gelöscht"
    )


@router.get("/upload/crest/{discord_id}")
def get_crest(discord_id: str, db: Session = Depends(get_db)):
    """Public Endpoint: Wappen des Teams eines Users abrufen (Redirect)."""
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    team = db.get(models.Team, user.team_id) if user and user.team_id else None
    if not team or not team.logo_url:
        raise HTTPException(status_code=404, detail="Wappen nicht gefunden")

    return RedirectResponse(url=team.logo_url)
