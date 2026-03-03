import os
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..auth import get_current_user
from ..image_utils import validate_image_file, process_crest_image

router = APIRouter()

# Upload-Verzeichnis aus Environment
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
CRESTS_DIR = os.path.join(UPLOAD_DIR, "crests")

# Sicherstellen dass Upload-Verzeichnis existiert
os.makedirs(CRESTS_DIR, exist_ok=True)


@router.post("/upload/crest", response_model=schemas.CrestUploadResponse)
async def upload_crest(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Wappen-Upload für eingeloggten User."""
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == current_user
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User-Profil nicht gefunden"
        )

    file_content = await file.read()
    file_size = len(file_content)

    is_valid, error_msg = validate_image_file(
        file.filename,
        file.content_type,
        file_size
    )

    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        processed_image = await process_crest_image(file_content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    filename = f"{user.discord_id}.webp"
    filepath = os.path.join(CRESTS_DIR, filename)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(processed_image)

    crest_url = f"/uploads/crests/{filename}"

    user.crest_url = crest_url
    db.commit()

    return schemas.CrestUploadResponse(
        crest_url=crest_url,
        message="Wappen erfolgreich hochgeladen"
    )


@router.delete("/upload/crest", response_model=schemas.CrestDeleteResponse)
async def delete_crest(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Löscht eigenes Wappen."""
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == current_user
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User-Profil nicht gefunden")

    if not user.crest_url:
        raise HTTPException(status_code=404, detail="Kein Wappen vorhanden")

    filename = f"{user.discord_id}.webp"
    filepath = os.path.join(CRESTS_DIR, filename)

    if os.path.exists(filepath):
        os.remove(filepath)

    user.crest_url = None
    db.commit()

    return schemas.CrestDeleteResponse(
        message="Wappen erfolgreich gelöscht"
    )


@router.get("/upload/crest/{discord_id}")
def get_crest(discord_id: str, db: Session = Depends(get_db)):
    """Public Endpoint: Wappen eines Users abrufen."""
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    if not user or not user.crest_url:
        raise HTTPException(status_code=404, detail="Wappen nicht gefunden")

    return RedirectResponse(url=user.crest_url)
