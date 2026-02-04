#!/usr/bin/env python3
"""
Seed-Script für BIW Pokal Testdaten

Erstellt:
- 1 aktive Saison mit 16 Teams in 4 Gruppen
- Vollständige Spielpläne (Gruppenphase)
- Teilweise eingetragene Ergebnisse
- KO-Bracket mit teilweise gespielten Matches
- News-Artikel

Usage:
    python seed.py [--clear]

    --clear: Löscht die Datenbank vor dem Seeding
"""

import sys
import os
import random
import requests
from datetime import datetime

# API Config
API_URL = "http://127.0.0.1:8000"
API_KEY = "biw-n8n-secret-key-change-me"  # Aus .env

HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

# Teamliste (NRW-typische Namen)
TEAMS = [
    "FC Schalke 04", "Borussia Dortmund", "Bayer 04 Leverkusen", "1. FC Köln",
    "Borussia Mönchengladbach", "VfL Bochum", "Fortuna Düsseldorf", "MSV Duisburg",
    "Rot-Weiss Essen", "Alemannia Aachen", "Wuppertaler SV", "SC Paderborn 07",
    "Arminia Bielefeld", "Preußen Münster", "Rot-Weiß Oberhausen", "KFC Uerdingen"
]

# News-Vorlagen
NEWS_TEMPLATES = [
    {
        "title": "BIW Pokal 2026 ist gestartet!",
        "content": """Die neue Saison des **BIW Pokals** hat begonnen!

16 Teams aus ganz Nordrhein-Westfalen kämpfen in 4 Gruppen um den Einzug in die KO-Phase.

**Gruppenphase:**
- Spieltag 1-3: Woche 39-41
- Jeder gegen jeden in der Gruppe
- Top 2 qualifizieren sich für die KO-Runde

Wir wünschen allen Teams viel Erfolg! ⚽""",
        "author": "Turnierleitung"
    },
    {
        "title": "Spieltag 1 abgeschlossen - Überraschungen!",
        "content": """Der erste Spieltag ist gespielt und brachte einige **Überraschungen**!

Besonders hervorzuheben:
- Mehrere Außenseiter konnten punkten
- Spannende Spiele bis zur letzten Minute
- Fair Play auf allen Plätzen

Die Tabellen sind nach dem ersten Spieltag noch eng zusammen. Alles ist offen!

*Nächster Spieltag: Woche 40*""",
        "author": "Spielberichterstatter"
    },
    {
        "title": "Halbzeit der Gruppenphase",
        "content": """Nach 2 Spieltagen zeichnet sich ab, wer in die KO-Phase einziehen könnte.

**Highlights:**
- Einige Teams ungeschlagen
- Torreiche Spiele
- Enge Entscheidungen in mehreren Gruppen

Wer schafft es in die Top 2? Der letzte Gruppenspieltag wird entscheiden!""",
        "author": "Admin"
    }
]


def clear_database():
    """Löscht die SQLite-Datenbank"""
    db_path = os.path.join(os.path.dirname(__file__), "biw.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        print("✓ Datenbank gelöscht")
    else:
        print("ℹ Keine Datenbank vorhanden")


def create_season(name, participant_count=16):
    """Erstellt eine neue Saison"""
    response = requests.post(
        f"{API_URL}/api/seasons",
        json={"name": name, "participant_count": participant_count},
        headers=HEADERS
    )
    response.raise_for_status()
    season = response.json()
    print(f"✓ Saison erstellt: {season['name']} (ID: {season['id']})")
    return season


def add_teams_bulk(season_id, team_names):
    """Fügt Teams per Bulk-Import hinzu"""
    response = requests.post(
        f"{API_URL}/api/seasons/{season_id}/teams/bulk",
        json={"teams": team_names},
        headers=HEADERS
    )
    response.raise_for_status()
    result = response.json()
    print(f"✓ {result['count']} Teams hinzugefügt")
    return result


def get_groups_with_teams(season_id):
    """Holt Gruppen mit Teams"""
    response = requests.get(f"{API_URL}/api/seasons/{season_id}/groups-with-teams")
    response.raise_for_status()
    return response.json()


def generate_group_schedule(group_id):
    """Generiert Spielplan für eine Gruppe"""
    response = requests.post(
        f"{API_URL}/api/groups/{group_id}/generate-schedule",
        headers=HEADERS
    )
    response.raise_for_status()
    return response.json()


def update_match_result(match_id, home_goals, away_goals):
    """Trägt Ergebnis für ein Match ein"""
    response = requests.patch(
        f"{API_URL}/api/matches/{match_id}",
        json={"home_goals": home_goals, "away_goals": away_goals},
        headers=HEADERS
    )
    response.raise_for_status()
    return response.json()


def generate_ko_bracket(season_id):
    """Generiert KO-Bracket"""
    response = requests.post(
        f"{API_URL}/api/seasons/{season_id}/ko-bracket/generate",
        headers=HEADERS
    )
    response.raise_for_status()
    print(f"✓ KO-Bracket generiert")
    return response.json()


def get_ko_bracket(season_id):
    """Holt KO-Bracket"""
    response = requests.get(f"{API_URL}/api/seasons/{season_id}/ko-bracket")
    response.raise_for_status()
    return response.json()


def update_ko_match(match_id, home_goals, away_goals):
    """Trägt KO-Match-Ergebnis ein"""
    response = requests.patch(
        f"{API_URL}/api/ko-matches/{match_id}",
        json={"home_goals": home_goals, "away_goals": away_goals},
        headers=HEADERS
    )
    response.raise_for_status()
    return response.json()


def create_news(title, content, author="Admin", published=1):
    """Erstellt einen News-Artikel"""
    response = requests.post(
        f"{API_URL}/api/news",
        json={
            "title": title,
            "content": content,
            "author": author,
            "published": published
        },
        headers=HEADERS
    )
    response.raise_for_status()
    news = response.json()
    print(f"✓ News erstellt: {news['title']}")
    return news


def generate_realistic_score():
    """Generiert ein realistisches Fußball-Ergebnis"""
    # Häufigere Ergebnisse: 0-3 Tore pro Team
    # Seltener: 4+ Tore
    weights = [0.15, 0.25, 0.25, 0.20, 0.10, 0.05]  # 0-5 Tore
    home = random.choices(range(6), weights=weights)[0]
    away = random.choices(range(6), weights=weights)[0]
    return home, away


def seed_active_season():
    """Erstellt eine aktive Saison mit Testdaten"""
    print("\n=== Aktive Saison 2026 ===")

    # 1. Saison erstellen
    season = create_season("Saison 2026", participant_count=16)
    season_id = season['id']

    # 2. Teams hinzufügen
    add_teams_bulk(season_id, TEAMS)

    # 3. Gruppen holen und Spielpläne generieren
    groups = get_groups_with_teams(season_id)
    print(f"\n✓ {len(groups)} Gruppen erstellt")

    for group in groups:
        group_id = group['group']['id']
        group_name = group['group']['name']
        result = generate_group_schedule(group_id)
        print(f"  - Gruppe {group_name}: {result['matches_created']} Matches generiert")

    # 4. Teilweise Ergebnisse eintragen (ca. 60% der Matches)
    print("\n=== Ergebnisse eintragen ===")
    groups = get_groups_with_teams(season_id)  # Refresh

    total_played = 0
    for group in groups:
        group_name = group['group']['name']
        matches = group['matches']

        # Spiele 60% der Matches aus
        num_to_play = int(len(matches) * 0.6)
        matches_to_play = random.sample(matches, num_to_play)

        for match in matches_to_play:
            home_goals, away_goals = generate_realistic_score()
            update_match_result(match['id'], home_goals, away_goals)
            total_played += 1

    print(f"✓ {total_played} Matches ausgespielt")

    # 5. KO-Bracket generieren
    print("\n=== KO-Bracket ===")
    ko_bracket = generate_ko_bracket(season_id)

    # 6. Einige KO-Matches ausspielen (erste Runde teilweise)
    bracket = get_ko_bracket(season_id)
    round1_matches = [m for m in bracket['matches'] if m['round'] == 1 and not m['is_bye']]

    # Spiele 50% der ersten Runde
    num_to_play = len(round1_matches) // 2
    for match in random.sample(round1_matches, num_to_play):
        if match['home_team_id'] and match['away_team_id']:
            home_goals, away_goals = generate_realistic_score()
            # Verhindere Unentschieden im KO
            while home_goals == away_goals:
                home_goals, away_goals = generate_realistic_score()
            update_ko_match(match['id'], home_goals, away_goals)

    print(f"✓ {num_to_play} KO-Matches ausgespielt (Runde 1)")

    # 7. News erstellen
    print("\n=== News ===")
    for news_data in NEWS_TEMPLATES:
        create_news(**news_data)

    print(f"\n✅ Aktive Saison erfolgreich angelegt!")


def seed_archived_season():
    """Erstellt eine abgeschlossene/archivierte Saison"""
    print("\n=== Archivierte Saison 2025 ===")

    # Kleinere Saison mit 12 Teams
    season = create_season("Saison 2025", participant_count=12)
    season_id = season['id']

    # 12 verschiedene Teams
    archive_teams = [
        "VfL Wolfsburg", "Hertha BSC", "1. FC Union Berlin", "FC St. Pauli",
        "Hamburger SV", "SV Werder Bremen", "Hannover 96", "Eintracht Braunschweig",
        "SC Freiburg", "1. FSV Mainz 05", "VfB Stuttgart", "Karlsruher SC"
    ]

    add_teams_bulk(season_id, archive_teams[:12])

    # Spielpläne generieren
    groups = get_groups_with_teams(season_id)
    for group in groups:
        generate_group_schedule(group['group']['id'])

    # Alle Matches ausspielen (Archiv = komplett)
    groups = get_groups_with_teams(season_id)
    for group in groups:
        for match in group['matches']:
            home_goals, away_goals = generate_realistic_score()
            update_match_result(match['id'], home_goals, away_goals)

    # KO komplett durchspielen
    ko_bracket = generate_ko_bracket(season_id)
    bracket = get_ko_bracket(season_id)

    for match in bracket['matches']:
        if not match['is_bye'] and match['home_team_id'] and match['away_team_id']:
            home_goals, away_goals = generate_realistic_score()
            while home_goals == away_goals:
                home_goals, away_goals = generate_realistic_score()
            update_ko_match(match['id'], home_goals, away_goals)

    print(f"✅ Archiv-Saison komplett ausgespielt!")


def main():
    """Hauptfunktion"""
    print("=" * 50)
    print("BIW Pokal - Seed Script")
    print("=" * 50)

    # Check ob --clear Flag gesetzt
    if "--clear" in sys.argv:
        print("\n⚠️  Datenbank wird gelöscht...")
        clear_database()
        print("⚠️  Bitte Backend neu starten, damit Tabellen neu erstellt werden!")
        print("⚠️  Dann dieses Script ohne --clear ausführen.\n")
        return

    try:
        # Backend-Health-Check
        response = requests.get(f"{API_URL}/health", timeout=2)
        response.raise_for_status()
        print("✓ Backend erreichbar\n")
    except Exception as e:
        print(f"❌ Backend nicht erreichbar: {e}")
        print("   Bitte Backend starten: uvicorn app.main:app --reload")
        sys.exit(1)

    try:
        # Seeding
        seed_active_season()
        seed_archived_season()  # Optional: aktivieren für Archiv-Daten

        print("\n" + "=" * 50)
        print("✅ SEEDING ERFOLGREICH!")
        print("=" * 50)
        print("\nÖffne: http://127.0.0.1:5500/index.html")
        print("Admin: http://127.0.0.1:5500/admin.html")
        print("       User: admin / Passwort: biw2026!")

    except Exception as e:
        print(f"\n❌ Fehler beim Seeding: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
