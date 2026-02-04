"""
Simple Auth: JWT für Browser, API-Key für n8n
"""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from dotenv import load_dotenv

load_dotenv()

# Config aus .env
ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
API_KEY = os.getenv("API_KEY", "change-me")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

security = HTTPBearer(auto_error=False)


def create_jwt_token(username: str) -> str:
    """JWT Token erstellen."""
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> Optional[str]:
    """JWT Token prüfen, gibt Username zurück oder None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def verify_credentials(username: str, password: str) -> bool:
    """Login-Daten prüfen."""
    return username == ADMIN_USER and password == ADMIN_PASSWORD


def verify_api_key(key: str) -> bool:
    """API-Key prüfen."""
    return key == API_KEY


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None),
) -> str:
    """
    Auth-Dependency: Akzeptiert entweder:
    - Bearer JWT Token (für Browser)
    - X-API-Key Header (für n8n)
    
    Gibt Username zurück oder wirft 401.
    """
    # 1. API-Key prüfen
    if x_api_key and verify_api_key(x_api_key):
        return "api-user"
    
    # 2. JWT Bearer Token prüfen
    if credentials:
        username = verify_jwt_token(credentials.credentials)
        if username:
            return username
    
    # 3. Kein gültiger Auth
    raise HTTPException(
        status_code=401,
        detail="Nicht autorisiert",
        headers={"WWW-Authenticate": "Bearer"},
    )


# Optional: Dependency die Auth nur prüft wenn vorhanden (für öffentliche + private Daten)
async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None),
) -> Optional[str]:
    """Wie get_current_user, aber gibt None statt 401 wenn nicht eingeloggt."""
    if x_api_key and verify_api_key(x_api_key):
        return "api-user"
    
    if credentials:
        username = verify_jwt_token(credentials.credentials)
        if username:
            return username
    
    return None
