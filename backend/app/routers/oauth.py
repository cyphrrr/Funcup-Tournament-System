import time
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..auth import create_jwt_token
from ..discord_oauth import DiscordOAuth2Client

router = APIRouter()

# OAuth2 Client initialisieren
discord_oauth = DiscordOAuth2Client()

# State Storage (in Production: Redis verwenden!)
oauth_states = {}  # {state: timestamp}
OAUTH_STATE_TTL = 600  # 10 Minuten


def _cleanup_oauth_states():
    """Entfernt abgelaufene OAuth States."""
    now = time.time()
    expired = [k for k, v in oauth_states.items() if now - v > OAUTH_STATE_TTL]
    for k in expired:
        del oauth_states[k]


@router.get("/auth/discord/login")
def discord_login():
    """Startet Discord OAuth2 Flow."""
    state = secrets.token_urlsafe(32)
    _cleanup_oauth_states()
    oauth_states[state] = time.time()

    auth_url = discord_oauth.get_authorization_url(state)

    return {"authorization_url": auth_url}


@router.get("/auth/discord/callback", response_model=schemas.OAuth2CallbackResponse)
async def discord_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Discord OAuth2 Callback."""
    _cleanup_oauth_states()
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Ungültiger State (CSRF)")

    del oauth_states[state]

    token = await discord_oauth.fetch_token(code)
    if not token:
        raise HTTPException(status_code=400, detail="Token Exchange fehlgeschlagen")

    discord_user = await discord_oauth.fetch_user_info(token["access_token"])
    if not discord_user:
        raise HTTPException(status_code=400, detail="Konnte User-Info nicht abrufen")

    discord_id = discord_user["id"]
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    if not user:
        user = models.UserProfile(
            discord_id=discord_id,
            discord_username=f"{discord_user['username']}#{discord_user['discriminator']}",
            discord_avatar_url=discord_user.get("avatar"),
            participating_next=True
        )
        db.add(user)
    else:
        user.discord_username = f"{discord_user['username']}#{discord_user['discriminator']}"
        user.discord_avatar_url = discord_user.get("avatar")

    user.access_token = token["access_token"]
    user.refresh_token = token.get("refresh_token")
    user.token_expires_at = datetime.fromtimestamp(token["expires_at"], tz=timezone.utc)

    db.commit()
    db.refresh(user)

    jwt_token = create_jwt_token(discord_id)

    team_name = None
    if user.team_id:
        team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
        if team:
            team_name = team.name

    user_response = schemas.UserProfileResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar_url=user.discord_avatar_url,
        team_id=user.team_id,
        team_name=team_name,
        profile_url=user.profile_url,
        participating_next=user.participating_next,
        crest_url=user.crest_url,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

    return schemas.OAuth2CallbackResponse(
        access_token=jwt_token,
        user=user_response
    )
