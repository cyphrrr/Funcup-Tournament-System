#!/usr/bin/env python3
"""
BIW Pokal - Automatischer Saison-Import von WordPress
Importiert nur Gruppenphasen (Teams + Matches), keine KO-Brackets.
"""

import requests
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict, Optional

# Konfiguration
WP_API_URL = "https://biw-pokal.de/wp-json/wp/v2/pages"
BACKEND_API = "http://localhost:8000/api"
API_KEY = "biw-n8n-secret-key-change-me"  # Aus .env

# Auth Header für Backend-API
HEADERS = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}


def get_all_season_pages() -> List[Dict]:
    """
    Holt alle Saison-Seiten von der WordPress API.
    Filtert nach Slugs die mit 's' beginnen und Zahlen enthalten.
    """
    all_pages = []
    page = 1
    per_page = 100

    while True:
        print(f"Lade WordPress-Seiten (Seite {page})...")
        response = requests.get(f"{WP_API_URL}?per_page={per_page}&page={page}")

        if response.status_code != 200:
            break

        pages = response.json()
        if not pages:
            break

        all_pages.extend(pages)
        page += 1

    # Filter: Nur Saison-Seiten (slug enthält 's' + Zahl)
    season_pages = []
    for page in all_pages:
        slug = page.get('slug', '')
        # Matches: s10-gruppenphase, s11-gruppe-a, s12-gruppe-b, etc.
        if re.match(r's\d+', slug):
            season_pages.append({
                'id': page['id'],
                'slug': slug,
                'title': page['title']['rendered'],
                'content': page['content']['rendered']
            })

    return season_pages


def extract_season_number(slug: str) -> Optional[int]:
    """Extrahiert die Saison-Nummer aus dem Slug (z.B. 's10-gruppenphase' -> 10)"""
    match = re.search(r's(\d+)', slug)
    return int(match.group(1)) if match else None


def extract_group_name(slug: str, title: str) -> Optional[str]:
    """Extrahiert Gruppennamen (z.B. 's11-gruppe-a' -> 'A')"""
    # Versuche aus Slug
    match = re.search(r'gruppe-([a-z])', slug.lower())
    if match:
        return match.group(1).upper()

    # Versuche aus Titel
    match = re.search(r'Gruppe\s+([A-Z])', title)
    if match:
        return match.group(1)

    return None


def parse_group_table(html: str) -> Dict:
    """
    Parst eine Gruppentabelle aus HTML.
    Extrahiert Teams aus der "Verein"-Spalte (2. Spalte).
    """
    soup = BeautifulSoup(html, 'html.parser')

    teams = []
    matches = []

    # Suche nach Tabellen
    tables = soup.find_all('table')

    for table in tables:
        # Nur tbody-Zeilen verarbeiten (keine Header)
        tbody = table.find('tbody')
        if not tbody:
            continue

        rows = tbody.find_all('tr')

        for row in rows:
            cells = row.find_all('td')

            # Tabelle muss mindestens 2 Spalten haben (Pos, Verein, ...)
            if len(cells) < 2:
                continue

            # Team-Name ist in der 2. Spalte ("Verein")
            verein_cell = cells[1]

            # Suche nach Link im Verein-Cell
            link = verein_cell.find('a')
            if link:
                team_name = link.get_text(strip=True)
                # Filter: Keine Zeitformate (HH:MM), keine kurzen Strings
                if team_name and len(team_name) > 2 and not re.match(r'^\d{1,2}:\d{2}$', team_name):
                    teams.append(team_name)
            else:
                # Fallback: Direkter Text (falls kein Link)
                team_name = verein_cell.get_text(strip=True)
                # Filter: Keine Zahlen, keine Zeitformate, keine kurzen Strings
                if team_name and not team_name.isdigit() and len(team_name) > 2 and not re.match(r'^\d{1,2}:\d{2}$', team_name):
                    teams.append(team_name)

    # TODO: Match-Extraktion aus HTML (je nach Plugin-Struktur)
    # Aktuell: Nur Teams extrahieren

    return {
        'teams': list(set(teams)),  # Duplikate entfernen
        'matches': matches
    }


def create_season(season_number: int, participant_count: int) -> Optional[int]:
    """Erstellt eine neue Saison via API"""
    payload = {
        "name": f"Saison {season_number}",
        "participant_count": participant_count,
        "status": "archived"  # Historische Saisons sind archived
    }

    response = requests.post(f"{BACKEND_API}/seasons", json=payload, headers=HEADERS)

    if response.status_code == 200:
        season = response.json()
        print(f"✓ Saison {season_number} erstellt (ID: {season['id']})")
        return season['id']
    else:
        print(f"✗ Fehler beim Erstellen von Saison {season_number}: {response.text}")
        return None


def add_teams_to_season(season_id: int, teams: List[str]) -> bool:
    """Fügt Teams zu einer Saison hinzu (Bulk-Import)"""
    payload = {"teams": teams}

    response = requests.post(
        f"{BACKEND_API}/seasons/{season_id}/teams/bulk",
        json=payload,
        headers=HEADERS
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✓ {result['count']} Teams hinzugefügt")
        return True
    else:
        print(f"✗ Fehler beim Hinzufügen der Teams: {response.text}")
        return False


def import_season_from_pages(season_number: int, pages: List[Dict]) -> bool:
    """
    Importiert eine komplette Saison aus einer oder mehreren WordPress-Seiten.
    """
    print(f"\n=== Import Saison {season_number} ===")
    print(f"Gefundene Seiten: {len(pages)}")

    # Schritt 1: Alle Teams aus allen Gruppen sammeln
    all_teams = set()

    for page in pages:
        print(f"  - {page['title']} ({page['slug']})")
        data = parse_group_table(page['content'])
        all_teams.update(data['teams'])

    teams_list = sorted(list(all_teams))
    print(f"\nGefundene Teams: {len(teams_list)}")
    for team in teams_list:
        print(f"  - {team}")

    if not teams_list:
        print("⚠ Keine Teams gefunden, überspringe Saison")
        return False

    # Schritt 2: Saison erstellen
    season_id = create_season(season_number, len(teams_list))
    if not season_id:
        return False

    # Schritt 3: Teams hinzufügen
    if not add_teams_to_season(season_id, teams_list):
        return False

    # TODO: Schritt 4: Matches importieren (später)

    print(f"✓ Saison {season_number} erfolgreich importiert")
    return True


def main():
    import sys

    print("BIW Pokal - Automatischer Saison-Import")
    print("=" * 50)

    # Schritt 1: Alle Saison-Seiten holen
    print("\n1. Lade alle Saison-Seiten von WordPress...")
    pages = get_all_season_pages()
    print(f"✓ {len(pages)} Saison-Seiten gefunden")

    # Schritt 2: Nach Saison-Nummer gruppieren
    seasons = {}
    for page in pages:
        season_num = extract_season_number(page['slug'])
        if season_num:
            if season_num not in seasons:
                seasons[season_num] = []
            seasons[season_num].append(page)

    print(f"\nGefundene Saisons: {sorted(seasons.keys())}")

    # Schritt 3: Command-Line Argument auslesen
    if len(sys.argv) < 2:
        print("\nVerwendung:")
        print("  python3 import_seasons.py all              # Alle Saisons")
        print("  python3 import_seasons.py 10,11,12         # Einzelne Saisons")
        print("  python3 import_seasons.py --list           # Nur Saisons auflisten")
        return

    choice = sys.argv[1].strip()

    if choice == '--list':
        print("\nVerfügbare Saisons:")
        for season_num in sorted(seasons.keys()):
            page_count = len(seasons[season_num])
            print(f"  Saison {season_num}: {page_count} Seite(n)")
        return

    if choice.lower() == 'all':
        seasons_to_import = sorted(seasons.keys())
    else:
        try:
            seasons_to_import = [int(s.strip()) for s in choice.split(',')]
        except ValueError:
            print("Ungültige Eingabe")
            return

    # Schritt 4: Import durchführen
    print(f"\nStarte Import für Saisons: {seasons_to_import}")

    for season_num in seasons_to_import:
        if season_num in seasons:
            import_season_from_pages(season_num, seasons[season_num])
        else:
            print(f"⚠ Saison {season_num} nicht in WordPress gefunden")

    print("\n✓ Import abgeschlossen!")


if __name__ == "__main__":
    main()
