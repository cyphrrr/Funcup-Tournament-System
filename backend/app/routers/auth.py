from fastapi import APIRouter, Depends
from .. import schemas
from ..auth import get_current_user, verify_credentials, create_jwt_token
from fastapi import HTTPException

router = APIRouter()


@router.post("/login", response_model=schemas.LoginResponse)
def login(request: schemas.LoginRequest):
    """Login mit Username/Passwort, gibt JWT Token zurück."""
    if not verify_credentials(request.username, request.password):
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")

    token = create_jwt_token(request.username)
    return schemas.LoginResponse(
        access_token=token,
        username=request.username,
    )


@router.get("/me")
def get_me(current_user: str = Depends(get_current_user)):
    """Gibt den aktuellen User zurück (Auth-Test)."""
    return {"username": current_user}
