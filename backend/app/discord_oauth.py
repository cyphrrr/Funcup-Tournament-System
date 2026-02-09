"""
Discord OAuth2 Client
Verwendet Authlib für Discord OAuth2 Flow
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import httpx
from authlib.integrations.starlette_client import OAuth
from authlib.oauth2.rfc6749 import OAuth2Token
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Discord OAuth2 Config aus Environment
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:8000/api/auth/discord/callback")

# Discord API Endpoints
DISCORD_API_BASE_URL = "https://discord.com/api/v10"
DISCORD_AUTHORIZE_URL = "https://discord.com/api/oauth2/authorize"
DISCORD_TOKEN_URL = "https://discord.com/api/oauth2/token"


class DiscordOAuth2Client:
    """Discord OAuth2 Client für User-Authentifizierung"""

    def __init__(self):
        """Initialisiert Discord OAuth2 Client"""
        self.client_id = DISCORD_CLIENT_ID
        self.client_secret = DISCORD_CLIENT_SECRET
        self.redirect_uri = DISCORD_REDIRECT_URI

        if not self.client_id or not self.client_secret:
            logger.warning(
                "⚠️ Discord OAuth2 nicht konfiguriert! "
                "DISCORD_CLIENT_ID und DISCORD_CLIENT_SECRET fehlen."
            )

    def get_authorization_url(self, state: str) -> str:
        """
        Generiert Discord OAuth2 Authorization URL.

        Args:
            state: CSRF State Token (für Security)

        Returns:
            str: Full Authorization URL für Redirect
        """
        # Scopes: identify (Username, ID, Avatar)
        scopes = "identify"

        url = (
            f"{DISCORD_AUTHORIZE_URL}"
            f"?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&response_type=code"
            f"&scope={scopes}"
            f"&state={state}"
        )

        logger.info(f"📤 Discord OAuth2 URL generiert mit state={state}")
        return url

    async def fetch_token(self, code: str) -> Optional[OAuth2Token]:
        """
        Tauscht Authorization Code gegen Access Token.

        Args:
            code: Authorization Code von Discord

        Returns:
            OAuth2Token mit access_token, refresh_token, expires_in
            None bei Fehler
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    DISCORD_TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                if response.status_code != 200:
                    error = response.json()
                    logger.error(f"❌ Discord Token Exchange fehlgeschlagen: {error}")
                    return None

                token_data = response.json()
                logger.info("✅ Discord Access Token erhalten")

                # OAuth2Token-kompatibles Dict zurückgeben
                return OAuth2Token({
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data.get("refresh_token"),
                    "token_type": token_data["token_type"],
                    "expires_in": token_data["expires_in"],
                    "expires_at": int(
                        (datetime.utcnow() + timedelta(seconds=token_data["expires_in"])).timestamp()
                    )
                })

        except Exception as e:
            logger.error(f"❌ Fehler bei Discord Token Exchange: {e}")
            return None

    async def fetch_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Holt User-Info von Discord API.

        Args:
            access_token: Discord Access Token

        Returns:
            Dict mit User-Daten (id, username, discriminator, avatar)
            None bei Fehler
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{DISCORD_API_BASE_URL}/users/@me",
                    headers={
                        "Authorization": f"Bearer {access_token}"
                    }
                )

                if response.status_code != 200:
                    error = response.json()
                    logger.error(f"❌ Discord User Info fehlgeschlagen: {error}")
                    return None

                user_data = response.json()
                logger.info(f"✅ Discord User Info erhalten: {user_data.get('username')}")

                # Avatar URL konstruieren
                avatar_hash = user_data.get("avatar")
                avatar_url = None
                if avatar_hash:
                    avatar_url = (
                        f"https://cdn.discordapp.com/avatars/"
                        f"{user_data['id']}/{avatar_hash}.png?size=256"
                    )

                return {
                    "id": user_data["id"],
                    "username": user_data["username"],
                    "discriminator": user_data.get("discriminator", "0"),
                    "avatar": avatar_url,
                    "email": user_data.get("email"),
                }

        except Exception as e:
            logger.error(f"❌ Fehler bei Discord User Info: {e}")
            return None

    async def refresh_access_token(self, refresh_token: str) -> Optional[OAuth2Token]:
        """
        Erneuert Access Token via Refresh Token.

        Args:
            refresh_token: Discord Refresh Token

        Returns:
            Neues OAuth2Token oder None bei Fehler
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    DISCORD_TOKEN_URL,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "grant_type": "refresh_token",
                        "refresh_token": refresh_token,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )

                if response.status_code != 200:
                    error = response.json()
                    logger.error(f"❌ Token Refresh fehlgeschlagen: {error}")
                    return None

                token_data = response.json()
                logger.info("✅ Discord Token erfolgreich refreshed")

                return OAuth2Token({
                    "access_token": token_data["access_token"],
                    "refresh_token": token_data.get("refresh_token", refresh_token),
                    "token_type": token_data["token_type"],
                    "expires_in": token_data["expires_in"],
                    "expires_at": int(
                        (datetime.utcnow() + timedelta(seconds=token_data["expires_in"])).timestamp()
                    )
                })

        except Exception as e:
            logger.error(f"❌ Fehler bei Token Refresh: {e}")
            return None
