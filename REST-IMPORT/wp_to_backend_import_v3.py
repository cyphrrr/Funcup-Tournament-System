#!/usr/bin/env python3
"""
BIW Pokal - WordPress REST API to Backend Importer (v3)
Importiert Turnierdaten direkt von WordPress/SportsPress REST API ins FastAPI Backend.

v3 Fixes:
- ALLE Leagues laden via Pagination (nicht nur erste 100)
- Leagues nach Name filtern statt nach Season-ID (WordPress-Bug)
- Robustes Ergebnis-Parsing
"""

import requests
import logging
import time
import sys
import re
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

# ============================================================================
# KONFIGURATION
# ============================================================================

# WordPress REST API
WP_BASE_URL = "https://biw-pokal.de/wp-json/sportspress/v2"
WP_AUTH = ("Geschäftsführer", "WxuJ J9fp IC6d ogbP hxbQ SDAZ")  # Basic Auth

# Backend API
BACKEND_URL = "http://192.168.178.51:8000"
BACKEND_API_KEY = "biw-n8n-secret-key-change-me"

# Import-Einstellungen
SEASON_START = 10
SEASON_END = 50
PARTICIPANT_COUNT = 64  # Für 16 Groups (A-P)
REQUEST_DELAY = 0.1  # Sekunden zwischen Requests

# ============================================================================
# LOGGING SETUP
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wp_import_v3.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def safe_int(val) -> int:
    """Sicher einen Wert zu Integer konvertieren. Gibt 0 zurück bei Fehlern."""
    if val is None:
        return 0
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        val = val.strip()
        if val == '' or val == '-' or val == 'null':
            return 0
        try:
            return int(val)
        except ValueError:
            return 0
    return 0


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ImportStats:
    seasons_created: int = 0
    groups_fetched: int = 0
    teams_created: int = 0
    matches_created: int = 0
    matches_skipped: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


# ============================================================================
# WORDPRESS API CLIENT
# ============================================================================

class WordPressClient:
    """Client für WordPress/SportsPress REST API"""
    
    def __init__(self, base_url: str, auth: tuple):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.auth = auth
        
        # Cache für alle Leagues (einmal laden, mehrfach nutzen)
        self._all_leagues_cache: Optional[List[Dict]] = None
        
    def get_seasons(self) -> List[Dict]:
        """Alle Seasons abrufen"""
        url = f"{self.base_url}/seasons"
        params = {"per_page": 100}
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_teams(self) -> List[Dict]:
        """Alle Teams abrufen (für ID → Name Mapping)"""
        all_teams = []
        page = 1

        while True:
            url = f"{self.base_url}/teams"
            params = {"per_page": 100, "page": page, "status": "publish"}

            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                teams = response.json()
            except requests.exceptions.HTTPError as e:
                # WordPress API gibt 400 wenn keine weitere Seite existiert
                if e.response.status_code == 400:
                    logger.info(f"Reached end of teams at page {page} (WordPress returned 400)")
                    break
                raise

            if not teams:
                break

            all_teams.extend(teams)
            page += 1
            time.sleep(REQUEST_DELAY)

            # Safety limit
            if page > 10:
                break

        return all_teams
    
    def get_all_leagues(self) -> List[Dict]:
        """ALLE Leagues laden mit Pagination (cached)"""
        if self._all_leagues_cache is not None:
            return self._all_leagues_cache
            
        logger.info("Loading ALL leagues from WordPress (with pagination)...")
        all_leagues = []
        page = 1
        
        while True:
            url = f"{self.base_url}/leagues"
            params = {"per_page": 100, "page": page}

            try:
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                leagues = response.json()
            except requests.exceptions.HTTPError as e:
                # WordPress API gibt 400 wenn keine weitere Seite existiert
                if e.response.status_code == 400:
                    logger.info(f"  Reached end of leagues at page {page} (WordPress returned 400)")
                    break
                raise

            if not leagues:
                break

            all_leagues.extend(leagues)
            logger.info(f"  Page {page}: {len(leagues)} leagues (total: {len(all_leagues)})")
            page += 1
            time.sleep(REQUEST_DELAY)

            # Safety limit (6 Seiten erwartet, max 10)
            if page > 10:
                logger.warning("  Hit page limit (10), stopping")
                break
        
        logger.info(f"✓ Loaded {len(all_leagues)} leagues total")
        self._all_leagues_cache = all_leagues
        return all_leagues
    
    def get_leagues_for_season_by_name(self, season_number: int) -> List[Dict]:
        """Leagues für eine Season anhand des Namens filtern (BIW-XX-A bis BIW-XX-P)"""
        all_leagues = self.get_all_leagues()
        
        # Filter: BIW-{season_number}-[A-P] (keine KO-Ligen)
        pattern = re.compile(rf'^BIW-{season_number}-[A-P]$')
        
        return [l for l in all_leagues if pattern.match(l.get('name', ''))]
    
    def get_matches_for_league(self, league_wp_id: int) -> List[Dict]:
        """Matches für eine League abrufen"""
        url = f"{self.base_url}/events"
        params = {"leagues": league_wp_id, "per_page": 100}
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()


# ============================================================================
# BACKEND API CLIENT
# ============================================================================

class BackendClient:
    """Client für FastAPI Backend"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})
        
    def test_connection(self) -> bool:
        """Verbindung testen"""
        try:
            response = self.session.get(f"{self.base_url}/api/seasons", timeout=5)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Backend connection failed: {e}")
            return False
    
    def create_season(self, name: str, participant_count: int, status: str = "archived") -> Optional[Dict]:
        """Season erstellen (Groups werden automatisch generiert)"""
        url = f"{self.base_url}/api/seasons"
        payload = {
            "name": name,
            "participant_count": participant_count,
            "status": status
        }
        
        response = self.session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def get_season_groups(self, season_id: int) -> List[Dict]:
        """Groups einer Season abrufen"""
        url = f"{self.base_url}/api/seasons/{season_id}/groups"
        
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def create_team(self, season_id: int, name: str, group_id: int) -> Optional[Dict]:
        """Team in Season/Group erstellen"""
        url = f"{self.base_url}/api/seasons/{season_id}/teams"
        payload = {
            "name": name,
            "group_id": group_id
        }
        
        response = self.session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    
    def create_match(self, group_id: int, home_team_id: int, away_team_id: int,
                     home_goals: int, away_goals: int, status: str, matchday: int = 1) -> Optional[Dict]:
        """Match in Group erstellen"""
        url = f"{self.base_url}/api/groups/{group_id}/matches"
        payload = {
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "status": status,
            "matchday": matchday
        }
        
        response = self.session.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()


# ============================================================================
# MAIN IMPORTER
# ============================================================================

class BIWImporter:
    """Hauptklasse für den Import"""
    
    def __init__(self):
        self.wp = WordPressClient(WP_BASE_URL, WP_AUTH)
        self.backend = BackendClient(BACKEND_URL, BACKEND_API_KEY)
        self.stats = ImportStats()
        
        # Mappings
        self.wp_team_id_to_name: Dict[int, str] = {}  # WordPress Team ID → Name
        self.team_name_to_backend_id: Dict[str, int] = {}  # Team Name → Backend ID (per season reset)
        
    def load_team_mapping(self):
        """WordPress Team-Mapping laden"""
        logger.info("Loading WordPress teams...")
        
        teams = self.wp.get_teams()
        
        for team in teams:
            wp_id = team['id']
            name = team['title']['rendered']
            self.wp_team_id_to_name[wp_id] = name
            
        logger.info(f"✓ Loaded {len(self.wp_team_id_to_name)} teams")
    
    def extract_group_letter(self, league_name: str) -> Optional[str]:
        """Gruppen-Buchstabe aus League-Name extrahieren"""
        match = re.search(r'BIW-\d+-([A-P])$', league_name)
        return match.group(1) if match else None
    
    def import_season(self, season_number: int) -> bool:
        """Eine Season komplett importieren"""
        season_name = f"Saison {season_number}"
        
        logger.info(f"\n{'='*60}")
        logger.info(f"IMPORTING {season_name}")
        logger.info(f"{'='*60}")
        
        # Team-Mapping für diese Season zurücksetzen
        self.team_name_to_backend_id = {}
        
        # 1. Leagues für diese Season finden (nach Name, nicht nach ID!)
        group_leagues = self.wp.get_leagues_for_season_by_name(season_number)
        logger.info(f"✓ Found {len(group_leagues)} group leagues for Season {season_number}")
        
        if not group_leagues:
            logger.warning(f"  No leagues found for Season {season_number}, skipping")
            return False
        
        # 2. Season im Backend erstellen
        try:
            status = "archived" if season_number < 50 else "active"
            backend_season = self.backend.create_season(season_name, PARTICIPANT_COUNT, status)
            backend_season_id = backend_season['id']
            logger.info(f"✓ Created Season (Backend ID: {backend_season_id})")
            self.stats.seasons_created += 1
        except Exception as e:
            error = f"Failed to create season {season_name}: {e}"
            logger.error(error)
            self.stats.errors.append(error)
            return False
        
        # 3. Backend Groups abrufen
        try:
            groups = self.backend.get_season_groups(backend_season_id)
            group_letter_to_id = {g['name']: g['id'] for g in groups}
            logger.info(f"✓ Retrieved {len(groups)} groups: {list(group_letter_to_id.keys())}")
            self.stats.groups_fetched += len(groups)
        except Exception as e:
            error = f"Failed to get groups for season {backend_season_id}: {e}"
            logger.error(error)
            self.stats.errors.append(error)
            return False
        
        # 4. Für jede League: Teams und Matches importieren
        for league in group_leagues:
            self.import_league(
                league=league,
                backend_season_id=backend_season_id,
                group_letter_to_id=group_letter_to_id
            )
            time.sleep(REQUEST_DELAY)
        
        logger.info(f"✓ Season {season_number} import complete")
        return True
    
    def import_league(self, league: Dict, backend_season_id: int, group_letter_to_id: Dict[str, int]):
        """Eine League (Gruppe) importieren"""
        league_name = league['name']
        league_wp_id = league['id']
        group_letter = self.extract_group_letter(league_name)
        
        if not group_letter:
            logger.warning(f"  Could not extract group letter from {league_name}")
            return
            
        group_id = group_letter_to_id.get(group_letter)
        if not group_id:
            logger.warning(f"  Group {group_letter} not found in backend")
            return
            
        logger.info(f"\n  --- Group {group_letter} (League: {league_name}) ---")
        
        # Matches abrufen
        try:
            wp_matches = self.wp.get_matches_for_league(league_wp_id)
            logger.info(f"  Found {len(wp_matches)} matches")
        except Exception as e:
            error = f"Failed to get matches for league {league_name}: {e}"
            logger.error(f"  {error}")
            self.stats.errors.append(error)
            return
        
        if not wp_matches:
            logger.info(f"  No matches in this league, skipping")
            return
        
        # Teams aus Matches extrahieren und erstellen
        teams_in_group: Set[str] = set()
        for match in wp_matches:
            for wp_team_id in match.get('teams', []):
                team_name = self.wp_team_id_to_name.get(wp_team_id)
                if team_name:
                    teams_in_group.add(team_name)
                else:
                    logger.warning(f"  Unknown team ID: {wp_team_id}")
        
        logger.info(f"  Creating {len(teams_in_group)} teams...")
        for team_name in teams_in_group:
            self.ensure_team_exists(backend_season_id, team_name, group_id)
            time.sleep(REQUEST_DELAY / 2)
        
        # Matches erstellen
        logger.info(f"  Creating {len(wp_matches)} matches...")
        matches_created = 0
        matches_skipped = 0
        
        for match in wp_matches:
            result = self.create_match_from_wp(match, group_id)
            if result == "created":
                matches_created += 1
            elif result == "skipped":
                matches_skipped += 1
            time.sleep(REQUEST_DELAY / 2)
        
        logger.info(f"  ✓ Created {matches_created}/{len(wp_matches)} matches")
    
    def ensure_team_exists(self, season_id: int, team_name: str, group_id: int):
        """Team erstellen falls nicht vorhanden"""
        if team_name in self.team_name_to_backend_id:
            return  # Bereits erstellt in dieser Season
            
        try:
            result = self.backend.create_team(season_id, team_name, group_id)
            backend_id = result['id']
            self.team_name_to_backend_id[team_name] = backend_id
            self.stats.teams_created += 1
            logger.debug(f"    Created team '{team_name}' (ID: {backend_id})")
        except requests.HTTPError as e:
            if e.response.status_code == 409:  # Duplicate
                logger.debug(f"    Team '{team_name}' already exists")
            else:
                error = f"Failed to create team '{team_name}': {e}"
                logger.error(f"    {error}")
                self.stats.errors.append(error)
        except Exception as e:
            error = f"Failed to create team '{team_name}': {e}"
            logger.error(f"    {error}")
            self.stats.errors.append(error)
    
    def create_match_from_wp(self, wp_match: Dict, group_id: int) -> str:
        """Match aus WordPress-Daten erstellen. Returns: 'created', 'skipped', oder 'error'"""
        teams = wp_match.get('teams', [])
        if len(teams) != 2:
            logger.warning(f"    Match has {len(teams)} teams, expected 2")
            return "error"
        
        wp_home_id, wp_away_id = teams[0], teams[1]
        
        home_name = self.wp_team_id_to_name.get(wp_home_id)
        away_name = self.wp_team_id_to_name.get(wp_away_id)
        
        if not home_name or not away_name:
            logger.warning(f"    Unknown team IDs: {wp_home_id}, {wp_away_id}")
            return "error"
        
        home_id = self.team_name_to_backend_id.get(home_name)
        away_id = self.team_name_to_backend_id.get(away_name)
        
        if not home_id or not away_id:
            logger.warning(f"    Teams not in backend: {home_name}, {away_name}")
            return "error"
        
        # Ergebnis parsen mit safe_int()
        main_results = wp_match.get('main_results', [])
        home_goals = safe_int(main_results[0]) if len(main_results) > 0 else 0
        away_goals = safe_int(main_results[1]) if len(main_results) > 1 else 0
        
        # Status bestimmen - prüfe ob es ein echtes Ergebnis gibt
        raw_home = main_results[0] if len(main_results) > 0 else None
        raw_away = main_results[1] if len(main_results) > 1 else None
        
        has_valid_result = False
        try:
            if raw_home is not None and raw_away is not None:
                if str(raw_home).strip() not in ('', '-', 'null') and str(raw_away).strip() not in ('', '-', 'null'):
                    int(raw_home)
                    int(raw_away)
                    has_valid_result = True
        except (ValueError, TypeError):
            pass
        
        status = "played" if has_valid_result else "scheduled"
        
        try:
            self.backend.create_match(group_id, home_id, away_id, home_goals, away_goals, status)
            self.stats.matches_created += 1
            return "created"
        except Exception as e:
            error = f"Failed to create match {home_name} vs {away_name}: {e}"
            logger.error(f"    {error}")
            self.stats.errors.append(error)
            return "error"
    
    def print_summary(self):
        """Zusammenfassung ausgeben"""
        logger.info(f"\n{'='*60}")
        logger.info("IMPORT SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Seasons created:  {self.stats.seasons_created}")
        logger.info(f"Groups fetched:   {self.stats.groups_fetched}")
        logger.info(f"Teams created:    {self.stats.teams_created}")
        logger.info(f"Matches created:  {self.stats.matches_created}")
        logger.info(f"Errors:           {len(self.stats.errors)}")
        
        if self.stats.errors:
            logger.warning("\nFirst 10 errors:")
            for error in self.stats.errors[:10]:
                logger.warning(f"  - {error}")
            if len(self.stats.errors) > 10:
                logger.warning(f"  ... and {len(self.stats.errors) - 10} more")
        
        logger.info(f"{'='*60}")
    
    def run(self):
        """Import ausführen"""
        logger.info("="*60)
        logger.info("BIW POKAL - WORDPRESS TO BACKEND IMPORT (v3)")
        logger.info("="*60)
        logger.info(f"WordPress API: {WP_BASE_URL}")
        logger.info(f"Backend API:   {BACKEND_URL}")
        logger.info(f"Seasons:       {SEASON_START} - {SEASON_END}")
        logger.info("="*60)
        
        # Backend-Verbindung testen
        if not self.backend.test_connection():
            logger.error("Cannot connect to backend. Aborting.")
            sys.exit(1)
        logger.info("✓ Backend connection OK")
        
        # Team-Mapping laden
        self.load_team_mapping()
        
        # ALLE Leagues vorab laden (mit Pagination)
        self.wp.get_all_leagues()
        
        # Import für jede Season (10-50)
        for season_number in range(SEASON_START, SEASON_END + 1):
            try:
                self.import_season(season_number)
                time.sleep(0.5)  # Kurze Pause zwischen Seasons
            except KeyboardInterrupt:
                logger.warning("\nImport interrupted by user")
                break
            except Exception as e:
                error = f"Fatal error importing season {season_number}: {e}"
                logger.error(error, exc_info=True)
                self.stats.errors.append(error)
                continue
        
        self.print_summary()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    importer = BIWImporter()
    importer.run()
