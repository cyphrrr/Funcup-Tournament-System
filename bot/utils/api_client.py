"""
API Client für Backend-Kommunikation
Asynchroner HTTP Client mit aiohttp
"""

import os
import logging
from typing import Optional, Dict, Any
import aiohttp

logger = logging.getLogger('biw-bot.api')


class BackendAPIClient:
    """Async HTTP Client für BIW Pokal Backend"""

    def __init__(self, base_url: Optional[str] = None):
        """
        Initialisiert den API Client

        Args:
            base_url: Backend URL (default: aus BACKEND_URL Environment Variable)
        """
        self.base_url = base_url or os.getenv('BACKEND_URL', 'http://backend:8000')
        self.base_url = self.base_url.rstrip('/')
        logger.info(f'🔗 API Client initialisiert: {self.base_url}')

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Führt HTTP Request aus

        Args:
            method: HTTP Methode (GET, POST, PATCH, etc.)
            endpoint: API Endpoint (z.B. '/api/teams')
            json_data: JSON Body für POST/PATCH
            params: Query Parameter

        Returns:
            Response als Dict oder None bei Fehler
        """
        url = f'{self.base_url}{endpoint}'

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    json=json_data,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    # Status Code prüfen
                    if response.status >= 400:
                        error_text = await response.text()
                        logger.error(
                            f'❌ API Error: {method} {endpoint} -> '
                            f'{response.status} {error_text}'
                        )
                        return None

                    # JSON Response parsen
                    data = await response.json()
                    logger.debug(f'✅ {method} {endpoint} -> {response.status}')
                    return data

        except aiohttp.ClientConnectorError:
            logger.error(f'❌ Backend nicht erreichbar: {self.base_url}')
            return None
        except aiohttp.ClientError as e:
            logger.error(f'❌ HTTP Error: {e}')
            return None
        except Exception as e:
            logger.error(f'❌ Unerwarteter Fehler bei API Request: {e}', exc_info=e)
            return None

    # --- Discord User Endpoints ---

    async def get_team_by_discord_id(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt User-Profil anhand der Discord User ID

        Args:
            discord_id: Discord User ID (String)

        Returns:
            User Dict mit Feldern: id, discord_id, team_name, profile_url, participating_next, etc.
            None wenn User nicht gefunden oder Fehler
        """
        return await self._request('GET', f'/api/discord/users/{discord_id}')

    async def set_participation(self, discord_id: str, participating: bool) -> bool:
        """
        Setzt Teilnahme-Status für nächsten Pokal

        Args:
            discord_id: Discord User ID
            participating: True = dabei, False = nicht dabei

        Returns:
            True bei Erfolg, False bei Fehler
        """
        result = await self._request(
            'PATCH',
            f'/api/discord/users/{discord_id}/participation',
            json_data={'participating': participating}
        )
        return result is not None

    async def set_profile_url(self, discord_id: str, url: str) -> bool:
        """
        Speichert Onlineliga Profil-URL

        Args:
            discord_id: Discord User ID
            url: Onlineliga Profil-URL

        Returns:
            True bei Erfolg, False bei Fehler
        """
        result = await self._request(
            'PATCH',
            f'/api/discord/users/{discord_id}/profile',
            json_data={'profile_url': url}
        )
        return result is not None

    async def get_user_status(self, discord_id: str) -> Optional[Dict[str, Any]]:
        """
        Holt vollständigen User-Status (Team, Teilnahme, Profil, etc.)

        Args:
            discord_id: Discord User ID

        Returns:
            Dict mit allen User-Daten oder None
        """
        return await self.get_team_by_discord_id(discord_id)

    # --- Health Check ---

    async def health_check(self) -> bool:
        """
        Prüft ob Backend erreichbar ist

        Returns:
            True wenn Backend antwortet, False sonst
        """
        result = await self._request('GET', '/health')
        return result is not None
