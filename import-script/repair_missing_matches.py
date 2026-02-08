#!/usr/bin/env python3
"""
Repariert fehlende Matches und Ergebnisse:
- Saison 12-25: Importiert fehlende Matches
- Saison 26-37: Aktualisiert Ergebnisse
"""

import requests
import json
import time
from pathlib import Path

API_URL = "http://localhost:8000"
API_KEY = "biw-n8n-secret-key-change-me"

headers = {"X-API-Key": API_KEY}

# JSON-Daten laden
with open("output/biw_data_xml_12-50_hinrunde.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Team-Cache (name -> id)
team_cache = {}

def get_team_id(team_name):
    """Holt Team-ID aus dem Cache oder von der API"""
    if team_name in team_cache:
        return team_cache[team_name]

    # Team über API suchen (vereinfacht - in Produktion würde man hier eine Search-API verwenden)
    # Für jetzt: Wir gehen davon aus, dass Teams bereits im Cache sind
    return None

def get_season_id_by_name(season_name):
    """Findet die Season-ID anhand des Namens"""
    response = requests.get(f"{API_URL}/api/seasons", headers=headers)
    seasons = response.json()

    for season in seasons:
        if season['name'] == season_name:
            return season['id']

    return None

def get_group_id(season_id, group_name):
    """Findet die Group-ID anhand der Season und des Gruppennamens"""
    response = requests.get(f"{API_URL}/api/seasons/{season_id}/groups", headers=headers)
    groups = response.json()

    for group in groups:
        if group['name'] == group_name:
            return group['id']

    return None

def build_team_cache():
    """Baut den Team-Cache auf"""
    print("Baue Team-Cache auf...")

    # Alle Saisonen durchgehen und Teams sammeln
    response = requests.get(f"{API_URL}/api/seasons", headers=headers)
    seasons = response.json()

    for season in seasons:
        response = requests.get(f"{API_URL}/api/seasons/{season['id']}/groups-with-teams", headers=headers)
        groups_data = response.json()

        for group_data in groups_data:
            for team in group_data['teams']:
                team_cache[team['name']] = team['id']

    print(f"✓ Team-Cache aufgebaut: {len(team_cache)} Teams")

def create_match(group_id, match_data, team_cache):
    """Erstellt ein Match"""
    home_team_id = team_cache.get(match_data['home_team'])
    away_team_id = team_cache.get(match_data['away_team'])

    if not home_team_id or not away_team_id:
        print(f"    ✗ Teams nicht gefunden: {match_data['home_team']} vs {match_data['away_team']}")
        return False

    payload = {
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_goals": match_data['home_goals'],
        "away_goals": match_data['away_goals'],
        "status": match_data['status'],
        "matchday": match_data['matchday'],
        "ingame_week": match_data.get('matchday', 1)
    }

    try:
        response = requests.post(f"{API_URL}/api/groups/{group_id}/matches", json=payload, headers=headers)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"    ✗ Fehler: {str(e)}")
        return False

def update_match_result(match_id, home_goals, away_goals):
    """Aktualisiert das Ergebnis eines Matches"""
    payload = {
        "home_goals": home_goals,
        "away_goals": away_goals
    }

    try:
        response = requests.patch(f"{API_URL}/api/matches/{match_id}", json=payload, headers=headers)
        response.raise_for_status()
        return True
    except Exception as e:
        return False

def repair_seasons_12_25(data, team_cache):
    """Importiert fehlende Matches für Saison 12-25"""
    print("\n" + "="*60)
    print("REPARATUR: Saison 12-25 (fehlende Matches)")
    print("="*60)

    stats = {'created': 0, 'errors': 0}

    for season_data in data['seasons']:
        season_number = season_data['season']

        if not (12 <= season_number <= 25):
            continue

        season_name = f"Saison {season_number}"
        season_id = get_season_id_by_name(season_name)

        if not season_id:
            print(f"✗ Saison {season_number} nicht gefunden")
            continue

        print(f"\n  Saison {season_number} (ID: {season_id})...")

        for group_data in season_data['groups']:
            group_name = group_data['group']
            group_id = get_group_id(season_id, group_name)

            if not group_id:
                print(f"    ✗ Gruppe {group_name} nicht gefunden")
                continue

            # Prüfen, wie viele Matches bereits existieren
            response = requests.get(f"{API_URL}/api/seasons/{season_id}/groups-with-teams", headers=headers)
            groups_with_teams = response.json()

            existing_matches = 0
            for g in groups_with_teams:
                if g['group']['name'] == group_name:
                    existing_matches = len(g['matches'])
                    break

            expected_matches = len(group_data['matches'])

            if existing_matches >= expected_matches:
                print(f"    ✓ Gruppe {group_name}: {existing_matches}/{expected_matches} Matches (OK)")
                continue

            print(f"    → Gruppe {group_name}: {existing_matches}/{expected_matches} Matches (importiere fehlende)")

            for match in group_data['matches']:
                if create_match(group_id, match, team_cache):
                    stats['created'] += 1
                else:
                    stats['errors'] += 1

                time.sleep(0.05)

    print(f"\n✓ Saison 12-25: {stats['created']} Matches erstellt, {stats['errors']} Fehler")
    return stats

def repair_seasons_26_37(data, team_cache):
    """Aktualisiert Ergebnisse für Saison 26-37"""
    print("\n" + "="*60)
    print("REPARATUR: Saison 26-37 (Ergebnisse nachtragen)")
    print("="*60)

    stats = {'updated': 0, 'skipped': 0, 'errors': 0}

    for season_data in data['seasons']:
        season_number = season_data['season']

        if not (26 <= season_number <= 37):
            continue

        season_name = f"Saison {season_number}"
        season_id = get_season_id_by_name(season_name)

        if not season_id:
            print(f"✗ Saison {season_number} nicht gefunden")
            continue

        print(f"\n  Saison {season_number} (ID: {season_id})...")

        # Alle Matches dieser Saison holen
        response = requests.get(f"{API_URL}/api/seasons/{season_id}/groups-with-teams", headers=headers)
        groups_with_teams = response.json()

        # Match-Mapping erstellen: (home_team_id, away_team_id) -> match_id
        match_map = {}
        for group_data in groups_with_teams:
            for match in group_data['matches']:
                key = (match['home_team_id'], match['away_team_id'])
                match_map[key] = match

        # Ergebnisse aus JSON aktualisieren
        for group_data in season_data['groups']:
            for match_data in group_data['matches']:
                home_team_id = team_cache.get(match_data['home_team'])
                away_team_id = team_cache.get(match_data['away_team'])

                if not home_team_id or not away_team_id:
                    stats['errors'] += 1
                    continue

                key = (home_team_id, away_team_id)

                if key not in match_map:
                    stats['errors'] += 1
                    continue

                match = match_map[key]

                # Nur aktualisieren, wenn Ergebnis fehlt und in JSON vorhanden
                if match['home_goals'] is None and match_data['home_goals'] is not None:
                    if update_match_result(match['id'], match_data['home_goals'], match_data['away_goals']):
                        stats['updated'] += 1
                    else:
                        stats['errors'] += 1
                else:
                    stats['skipped'] += 1

                time.sleep(0.02)

    print(f"\n✓ Saison 26-37: {stats['updated']} Ergebnisse aktualisiert, {stats['skipped']} übersprungen, {stats['errors']} Fehler")
    return stats

if __name__ == "__main__":
    print("="*60)
    print("MATCH-REPARATUR")
    print("="*60)

    # Team-Cache aufbauen
    build_team_cache()

    # Saison 12-25 reparieren (fehlende Matches)
    stats1 = repair_seasons_12_25(data, team_cache)

    # Saison 26-37 reparieren (Ergebnisse)
    stats2 = repair_seasons_26_37(data, team_cache)

    print("\n" + "="*60)
    print("ZUSAMMENFASSUNG")
    print("="*60)
    print(f"Matches erstellt:      {stats1['created']}")
    print(f"Ergebnisse aktualisiert: {stats2['updated']}")
    print(f"Gesamt Fehler:          {stats1['errors'] + stats2['errors']}")
    print("="*60)
