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
        self.api_key = os.getenv('API_KEY', '')
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
            headers = {}
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    json=json_data,
                    params=params,
                    headers=headers,
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

    async def ensure_user(
        self,
        discord_id: str,
        discord_username: str,
        discord_avatar_url: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Upsert User: Erstellt User falls nicht vorhanden, aktualisiert sonst.
        Wird bei jedem Command als erstes aufgerufen.

        Args:
            discord_id: Discord User ID (String)
            discord_username: Discord Username
            discord_avatar_url: Optional Discord Avatar URL

        Returns:
            User Dict mit allen Feldern oder None bei Fehler
        """
        return await self._request(
            'POST',
            '/api/discord/users/ensure',
            json_data={
                'discord_id': discord_id,
                'discord_username': discord_username,
                'discord_avatar_url': discord_avatar_url
            }
        )

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

    # --- Team Endpoints ---

    async def search_teams(self, name: str) -> list[Dict[str, Any]]:
        """
        Sucht Teams nach Name (partial match)

        Args:
            name: Team-Name (oder Teil davon)

        Returns:
            Liste von Teams (max. 10) oder leere Liste
        """
        result = await self._request(
            'GET',
            '/api/teams/search',
            params={'name': name}
        )
        return result if result else []

    async def claim_team(self, discord_id: str, team_id: int) -> Dict[str, Any]:
        """
        Claimed ein Team für einen User (Self-Service).

        Returns:
            Dict mit success/error Status:
            - {"success": True, "data": {...}} bei Erfolg
            - {"success": False, "error": "not_found"} bei 404
            - {"success": False, "error": "profile_url_required"} bei 403
            - {"success": False, "error": "already_has_team"} bei 409 (user hat schon team)
            - {"success": False, "error": "team_claimed"} bei 409 (team schon vergeben)
            - {"success": False, "error": "unknown"} bei anderen Fehlern
        """
        try:
            headers = {}
            if self.api_key:
                headers['X-API-Key'] = self.api_key
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/discord/users/{discord_id}/claim-team",
                    json={"team_id": team_id},
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {"success": True, "data": data}
                    elif resp.status == 403:
                        # Profile URL nicht gesetzt
                        error_data = await resp.json()
                        detail = error_data.get("detail", "")
                        if "PROFILE_URL_REQUIRED" in detail:
                            return {"success": False, "error": "profile_url_required"}
                        else:
                            return {"success": False, "error": "forbidden"}
                    elif resp.status == 404:
                        return {"success": False, "error": "not_found"}
                    elif resp.status == 409:
                        # Parse error message to distinguish between two cases
                        error_text = await resp.text()
                        if "bereits ein Team" in error_text:
                            return {"success": False, "error": "already_has_team"}
                        else:
                            return {"success": False, "error": "team_claimed"}
                    else:
                        error_text = await resp.text()
                        logger.error(f"Team-Claim fehlgeschlagen: {resp.status} {error_text}")
                        return {"success": False, "error": "unknown"}
        except Exception as e:
            logger.error(f"Team-Claim fehlgeschlagen: {e}")
            return {"success": False, "error": str(e)}

    # --- Spieltag / Turnier-Daten ---

    async def get_seasons(self) -> list:
        """
        Alle Saisons abrufen.

        Returns:
            Liste von Season-Dicts oder leere Liste
        """
        result = await self._request('GET', '/api/seasons')
        return result if result else []

    async def get_groups_with_teams(self, season_id: int) -> list:
        """
        Gruppen + Teams + Matches einer Saison abrufen.

        Returns:
            Liste von Group-Dicts (mit .group, .teams, .matches) oder leere Liste
        """
        result = await self._request('GET', f'/api/seasons/{season_id}/groups-with-teams')
        return result if result else []

    async def get_ko_brackets(self, season_id: int) -> dict:
        """
        Alle KO-Brackets einer Saison mit Matches abrufen.

        Returns:
            Dict mit season_id + brackets (meister/lucky_loser/loser) oder leeres Dict
        """
        result = await self._request('GET', f'/api/seasons/{season_id}/ko-brackets')
        return result if result else {}

    async def get_ko_brackets_status(self, season_id: int) -> dict:
        """
        KO-Bracket Status-Übersicht (für Verfügbarkeitsprüfung).

        Returns:
            Dict mit brackets_generated, brackets Status oder leeres Dict
        """
        result = await self._request('GET', f'/api/seasons/{season_id}/ko-brackets/status')
        return result if result else {}

    # --- Health Check ---

    async def health_check(self) -> bool:
        """
        Prüft ob Backend erreichbar ist

        Returns:
            True wenn Backend antwortet, False sonst
        """
        result = await self._request('GET', '/health')
        return result is not None
