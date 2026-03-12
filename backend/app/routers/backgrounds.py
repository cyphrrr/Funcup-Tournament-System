import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..auth import get_current_user
from ..image_utils import validate_image_file, process_background_image

router = APIRouter()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
BACKGROUNDS_DIR = os.path.join(UPLOAD_DIR, "backgrounds")
MAX_BG_FILE_SIZE = 10 * 1024 * 1024  # 10MB

os.makedirs(BACKGROUNDS_DIR, exist_ok=True)


def _bg_url(filename: str) -> str:
    return f"/uploads/backgrounds/{filename}"


@router.post("/backgrounds", response_model=schemas.BackgroundUploadResponse)
async def upload_background(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Neues Hintergrundbild hochladen."""
    file_content = await file.read()
    file_size = len(file_content)

    is_valid, error_msg = validate_image_file(
        file.filename, file.content_type, file_size,
        max_file_size=MAX_BG_FILE_SIZE
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        processed = await process_background_image(file_content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    filename = f"{uuid.uuid4().hex}.webp"
    filepath = os.path.join(BACKGROUNDS_DIR, filename)

    async with aiofiles.open(filepath, "wb") as f:
        await f.write(processed)

    bg = models.Background(
        filename=filename,
        original_name=file.filename
    )
    db.add(bg)
    db.commit()
    db.refresh(bg)

    return schemas.BackgroundUploadResponse(
        id=bg.id,
        filename=bg.filename,
        original_name=bg.original_name,
        url=_bg_url(bg.filename)
    )


@router.get("/backgrounds", response_model=list[schemas.BackgroundRead])
def list_backgrounds(db: Session = Depends(get_db)):
    """Alle Hintergrundbilder auflisten."""
    bgs = db.query(models.Background).order_by(models.Background.uploaded_at.desc()).all()
    return [
        schemas.BackgroundRead(
            id=bg.id,
            filename=bg.filename,
            original_name=bg.original_name,
            is_active=bg.is_active,
            opacity=bg.opacity,
            uploaded_at=bg.uploaded_at,
            url=_bg_url(bg.filename)
        )
        for bg in bgs
    ]


@router.get("/backgrounds/active")
def get_active_background(db: Session = Depends(get_db)):
    """Aktives Hintergrundbild abrufen. 204 wenn keins aktiv."""
    bg = db.query(models.Background).filter(models.Background.is_active == 1).first()
    if not bg:
        return JSONResponse(status_code=204, content=None)
    return schemas.BackgroundRead(
        id=bg.id,
        filename=bg.filename,
        original_name=bg.original_name,
        is_active=bg.is_active,
        opacity=bg.opacity,
        uploaded_at=bg.uploaded_at,
        url=_bg_url(bg.filename)
    )


@router.patch("/backgrounds/{bg_id}/activate", response_model=schemas.BackgroundActivateResponse)
def activate_background(
    bg_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Hintergrund aktivieren (deaktiviert alle anderen)."""
    bg = db.query(models.Background).get(bg_id)
    if not bg:
        raise HTTPException(status_code=404, detail="Hintergrundbild nicht gefunden")

    # Alle deaktivieren
    db.query(models.Background).update({"is_active": 0})
    bg.is_active = 1
    db.commit()

    return schemas.BackgroundActivateResponse(
        id=bg.id, is_active=1, message="Hintergrundbild aktiviert"
    )


@router.patch("/backgrounds/{bg_id}/deactivate", response_model=schemas.BackgroundActivateResponse)
def deactivate_background(
    bg_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Hintergrund deaktivieren (zurück zum Standard-Pattern)."""
    bg = db.query(models.Background).get(bg_id)
    if not bg:
        raise HTTPException(status_code=404, detail="Hintergrundbild nicht gefunden")

    bg.is_active = 0
    db.commit()

    return schemas.BackgroundActivateResponse(
        id=bg.id, is_active=0, message="Hintergrundbild deaktiviert"
    )


@router.patch("/backgrounds/{bg_id}", response_model=schemas.BackgroundRead)
def update_background_opacity(
    bg_id: int,
    data: schemas.BackgroundOpacityUpdate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Opacity eines Hintergrundbilds aktualisieren."""
    bg = db.query(models.Background).get(bg_id)
    if not bg:
        raise HTTPException(status_code=404, detail="Hintergrundbild nicht gefunden")

    bg.opacity = data.opacity
    db.commit()
    db.refresh(bg)

    return schemas.BackgroundRead(
        id=bg.id,
        filename=bg.filename,
        original_name=bg.original_name,
        is_active=bg.is_active,
        opacity=bg.opacity,
        uploaded_at=bg.uploaded_at,
        url=_bg_url(bg.filename)
    )


@router.delete("/backgrounds/{bg_id}", response_model=schemas.BackgroundDeleteResponse)
def delete_background(
    bg_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Hintergrundbild löschen (Datei + DB)."""
    bg = db.query(models.Background).get(bg_id)
    if not bg:
        raise HTTPException(status_code=404, detail="Hintergrundbild nicht gefunden")

    filepath = os.path.join(BACKGROUNDS_DIR, bg.filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    db.delete(bg)
    db.commit()

    return schemas.BackgroundDeleteResponse(message="Hintergrundbild erfolgreich gelöscht")
