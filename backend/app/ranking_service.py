"""
Google Sheets Ranking-Integration für Tiebreaker-Logik.

Dieses Modul holt Ranking-Daten aus einem öffentlichen Google Sheet
und verwendet sie als Tiebreaker bei KO-Matches mit Unentschieden.

Google Sheet: https://docs.google.com/spreadsheets/d/11EkZgWIZj7lyVrJ_PcXHz3kEY61QLDn-jrwyZvda0Ds/
Spaltenstruktur (erster Tab):
    - A (Index 0): teamName       ← für Team-Lookup
    - B (Index 1): Ø-Wert         ← Tiebreaker-Wert (niedrigerer Wert = besser)

Beispiel:
    teamName         | Ø der Saisons 51,50,49
    -----------------|------------------------
    Fronx Finest     | 774,43
    11 Freunde 09    | 473,31  ← niedrigerer Wert = besser = gewinnt

Tiebreaker-Regel: NIEDRIGERES avg_ranking gewinnt.
Falls nicht gefunden: 9999.0 (schlechtestes Ranking)
"""

import csv
import re
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from . import models

# Google Sheet ID (öffentlich lesbar)
SHEET_ID = "11EkZgWIZj7lyVrJ_PcXHz3kEY61QLDn-jrwyZvda0Ds"

# Cache für Sheet-Daten (10 Minuten)
_sheet_cache: Dict[str, Dict] = {}


def get_active_tab_name(db: Session) -> str:
    """
    Ermittelt den Tab-Namen aus der aktiven Season.

    Logik:
    1. Suche Season mit status="active"
    2. Extrahiere Nummer aus Name (z.B. "Saison 51" → 51)
    3. Tab-Name: "TN {nummer}"
    4. Fallback: höchste archivierte Season
    5. Fallback: "TN 51" (hardcoded)

    Args:
        db: SQLAlchemy Session

    Returns:
        Tab-Name, z.B. "TN 51"
    """
    # 1. Aktive Season suchen
    active_season = db.query(models.Season).filter(
        models.Season.status == "active"
    ).first()

    if active_season:
        # Nummer aus Name extrahieren
        match = re.search(r'\d+', active_season.name)
        if match:
            number = match.group()
            return f"TN {number}"

    # 2. Fallback: Höchste archivierte Season
    archived_seasons = db.query(models.Season).filter(
        models.Season.status == "archived"
    ).order_by(models.Season.created_at.desc()).all()

    if archived_seasons:
        for season in archived_seasons:
            match = re.search(r'\d+', season.name)
            if match:
                number = match.group()
                return f"TN {number}"

    # 3. Fallback: Hardcoded
    return "TN 51"


def fetch_ranking_sheet(db: Session) -> List[Dict]:
    """
    Holt Ranking-Sheet von Google Sheets und parst es.

    CSV-URL-Format (ohne Tab-Parameter, lädt ersten Tab):
    https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv

    Spalten (Index-basiert):
    - Index 0 (A): teamName
    - Index 1 (B): Ø-Wert (Komma als Dezimaltrennzeichen)

    Cache: 10 Minuten

    Args:
        db: SQLAlchemy Session

    Returns:
        Liste von Dicts: [{"teamName": "...", "avg_ranking": 473.31}, ...]
        Bei Netzwerkfehler: leere Liste + Warning

    Raises:
        Keine - Fehler werden geloggt und Default-Werte verwendet
    """
    # Cache prüfen (Cache-Key ist jetzt fix "ranking")
    cache_key = "ranking"
    if cache_key in _sheet_cache:
        cached = _sheet_cache[cache_key]
        age = (datetime.utcnow() - cached["timestamp"]).total_seconds()
        if age < 600:  # 10 Minuten
            return cached["data"]

    # CSV-URL bauen (ohne Tab-Parameter → erster Tab)
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    try:
        # CSV fetchen
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # CSV parsen
        lines = response.text.splitlines()
        reader = csv.reader(lines)

        # Header überspringen
        next(reader, None)

        # Daten extrahieren
        rankings = []
        for row in reader:
            if len(row) < 2:
                continue  # Zeile zu kurz (mindestens 2 Spalten nötig)

            team_name = row[0].strip()  # Spalte A
            avg_value_str = row[1].strip()  # Spalte B

            if not team_name:
                continue

            # Ø-Wert parsen (Komma als Dezimaltrennzeichen)
            avg_ranking = 9999.0
            if avg_value_str:
                try:
                    # Komma durch Punkt ersetzen
                    avg_value_str = avg_value_str.replace(',', '.')
                    avg_ranking = float(avg_value_str)
                except ValueError:
                    avg_ranking = 9999.0

            rankings.append({
                "teamName": team_name,
                "avg_ranking": avg_ranking
            })

        # Cache speichern
        _sheet_cache[cache_key] = {
            "data": rankings,
            "timestamp": datetime.utcnow()
        }

        print(f"[ranking_service] Lade Ranking aus erstem Tab (aktuellem Tab): {len(rankings)} Teams geladen")
        return rankings

    except requests.RequestException as e:
        print(f"[ranking_service] WARNING: Konnte Ranking-Sheet nicht laden: {e}")
        return []
    except Exception as e:
        print(f"[ranking_service] WARNING: Fehler beim Parsen des Ranking-Sheets: {e}")
        return []


def get_team_ranking(team_name: str, db: Session) -> float:
    """
    Gibt Ranking-Wert eines Teams zurück.

    Suche: Case-insensitive + Whitespace-trimming

    Args:
        team_name: Name des Teams
        db: SQLAlchemy Session

    Returns:
        avg_ranking (float) - niedrigerer Wert = besseres Ranking
        Falls nicht gefunden: 9999.0
    """
    rankings = fetch_ranking_sheet(db)
    team_name_normalized = team_name.strip().lower()

    for entry in rankings:
        if entry["teamName"].strip().lower() == team_name_normalized:
            return entry["avg_ranking"]

    # Nicht gefunden
    return 9999.0


def get_team_ranking_details(team_name: str, db: Session) -> Dict:
    """
    Gibt vollständige Ranking-Details eines Teams zurück.

    Args:
        team_name: Name des Teams
        db: SQLAlchemy Session

    Returns:
        Dict mit:
        - team_name: str
        - avg_ranking: float
        - tab_used: str (Info-Text über verwendeten Tab)
        - found: bool (ob Team im Sheet gefunden wurde)
    """
    rankings = fetch_ranking_sheet(db)
    team_name_normalized = team_name.strip().lower()

    for entry in rankings:
        if entry["teamName"].strip().lower() == team_name_normalized:
            return {
                "team_name": entry["teamName"],
                "avg_ranking": entry["avg_ranking"],
                "tab_used": "Erster Tab (aktuelles Ranking)",
                "found": True
            }

    # Nicht gefunden
    return {
        "team_name": team_name,
        "avg_ranking": 9999.0,
        "tab_used": "Erster Tab (aktuelles Ranking)",
        "found": False
    }


def resolve_tiebreaker(team1_id: int, team2_id: int, db: Session) -> Dict:
    """
    Entscheidet Unentschieden anhand Onlineliga-Ranking.

    Tiebreaker-Regel:
    - NIEDRIGERES avg_ranking gewinnt
    - Bei gleichem Wert: team1_id gewinnt (Heimvorteil)

    Args:
        team1_id: ID von Team 1 (Home)
        team2_id: ID von Team 2 (Away)
        db: SQLAlchemy Session

    Returns:
        Dict mit:
        - winner_id: int
        - team1_ranking: float
        - team2_ranking: float
        - tab_used: str
        - reason: str (menschenlesbare Begründung)

    Raises:
        ValueError: Wenn eines der Teams nicht existiert
    """
    # Teams laden
    team1 = db.get(models.Team, team1_id)
    team2 = db.get(models.Team, team2_id)

    if not team1:
        raise ValueError(f"Team mit ID {team1_id} nicht gefunden")
    if not team2:
        raise ValueError(f"Team mit ID {team2_id} nicht gefunden")

    # Rankings holen
    team1_ranking = get_team_ranking(team1.name, db)
    team2_ranking = get_team_ranking(team2.name, db)

    tab_used = "Erster Tab (aktuelles Ranking)"

    # Gewinner ermitteln (niedrigerer Wert = besser)
    if team1_ranking < team2_ranking:
        winner_id = team1_id
        reason = f"{team1.name} (Ø {team1_ranking}) schlägt {team2.name} (Ø {team2_ranking})"
    elif team2_ranking < team1_ranking:
        winner_id = team2_id
        reason = f"{team2.name} (Ø {team2_ranking}) schlägt {team1.name} (Ø {team1_ranking})"
    else:
        # Gleiches Ranking → Heimvorteil (team1)
        winner_id = team1_id
        reason = f"{team1.name} gewinnt durch Heimvorteil (beide Ø {team1_ranking})"

    return {
        "winner_id": winner_id,
        "team1_ranking": team1_ranking,
        "team2_ranking": team2_ranking,
        "tab_used": tab_used,
        "reason": reason
    }
