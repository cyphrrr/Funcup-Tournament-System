"""
KO-Bracket-Generierung für 3-Bracket-System.

Dieses Modul implementiert die Logik zur Generierung der drei KO-Brackets:
- Meister-Bracket: Gruppenerste
- Lucky-Loser-Bracket: Gruppenzweite
- Loser-Bracket: Gruppendritten

Features:
- Automatische Freilos-Berechnung bei nicht-Zweierpotenzen
- Gespiegeltes Seeding (Stärkster vs. Schwächster)
- Bracket-Persistenz (komplettes Bracket wird beim Generieren gespeichert)
- Automatische Sieger-Weiterleitung via next_match_id/next_match_slot
"""

from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import math

from . import models


def get_qualified_teams(season_id: int, db: Session) -> Dict[str, List[int]]:
    """
    Ermittelt qualifizierte Teams aus Gruppenphase.

    Prozess:
    1. Lade alle Gruppen der Saison
    2. Prüfe dass ALLE Gruppen abgeschlossen sind (alle Matches gespielt)
    3. Berechne Tabelle für jede Gruppe
    4. Extrahiere Platz 1, 2, 3 pro Gruppe
    5. Sortiere nach Gruppenname (A, B, C, ...)

    Args:
        season_id: ID der Saison
        db: SQLAlchemy Session

    Returns:
        Dict mit Keys "meister", "lucky_loser", "loser"
        Jeder Value: geordnete Liste von team_ids

    Raises:
        ValueError: Wenn nicht alle Gruppen abgeschlossen sind
    """
    # Alle Gruppen der Saison laden
    groups = db.query(models.Group).filter(
        models.Group.season_id == season_id
    ).order_by(models.Group.name).all()

    if not groups:
        raise ValueError(f"Keine Gruppen für Season {season_id} gefunden")

    # Prüfen ob alle Gruppen abgeschlossen sind
    for group in groups:
        matches = db.query(models.Match).filter(
            models.Match.group_id == group.id
        ).all()

        # Mindestens ein Match muss existieren
        if not matches:
            raise ValueError(f"Gruppe {group.name} hat keine Matches")

        # Alle Matches müssen gespielt sein
        unplayed = [m for m in matches if m.status != "played"]
        if unplayed:
            raise ValueError(
                f"Gruppe {group.name} nicht abgeschlossen: "
                f"{len(unplayed)} Matches noch nicht gespielt"
            )

    # Tabellen berechnen und Platzierungen extrahieren
    meister = []
    lucky_loser = []
    loser = []

    for group in groups:
        standings = _calculate_group_standings(group.id, db)

        # Platzierungen extrahieren (falls vorhanden)
        if len(standings) >= 1:
            meister.append(standings[0]["team_id"])
        if len(standings) >= 2:
            lucky_loser.append(standings[1]["team_id"])
        if len(standings) >= 3:
            loser.append(standings[2]["team_id"])

    return {
        "meister": meister,
        "lucky_loser": lucky_loser,
        "loser": loser
    }


def _calculate_group_standings(group_id: int, db: Session) -> List[Dict]:
    """
    Berechnet die Tabelle einer Gruppe (on-the-fly).

    Punkte: Sieg 3, Unentschieden 1, Niederlage 0
    Sortierung: Punkte DESC, Tordifferenz DESC, Tore DESC

    Args:
        group_id: ID der Gruppe
        db: SQLAlchemy Session

    Returns:
        Sortierte Liste von Team-Statistiken
    """
    matches = db.query(models.Match).filter(
        models.Match.group_id == group_id
    ).all()

    teams = {
        st.team_id: {
            "team_id": st.team_id,
            "played": 0,
            "won": 0,
            "draw": 0,
            "lost": 0,
            "goals_for": 0,
            "goals_against": 0,
            "points": 0,
        }
        for st in db.query(models.SeasonTeam).filter(
            models.SeasonTeam.group_id == group_id
        ).all()
    }

    for m in matches:
        if m.home_goals is None or m.away_goals is None:
            continue
        if m.home_team_id not in teams or m.away_team_id not in teams:
            continue

        home = teams[m.home_team_id]
        away = teams[m.away_team_id]

        home["played"] += 1
        away["played"] += 1
        home["goals_for"] += m.home_goals
        home["goals_against"] += m.away_goals
        away["goals_for"] += m.away_goals
        away["goals_against"] += m.home_goals

        if m.home_goals > m.away_goals:
            home["won"] += 1
            away["lost"] += 1
            home["points"] += 3
        elif m.home_goals < m.away_goals:
            away["won"] += 1
            home["lost"] += 1
            away["points"] += 3
        else:
            home["draw"] += 1
            away["draw"] += 1
            home["points"] += 1
            away["points"] += 1

    table = list(teams.values())
    table.sort(
        key=lambda x: (
            x["points"],
            x["goals_for"] - x["goals_against"],
            x["goals_for"]
        ),
        reverse=True
    )

    return table


def seed_teams(teams: List[int]) -> List[Tuple[int, int]]:
    """
    Gespiegeltes Seeding: Stärkster vs. Schwächster.

    Beispiel 8 Teams [A,B,C,D,E,F,G,H]:
    → Paarung 1: A vs H
    → Paarung 2: B vs G
    → Paarung 3: C vs F
    → Paarung 4: D vs E

    Args:
        teams: Geordnete Liste von team_ids (Platz 1 zuerst)

    Returns:
        Liste von Tupeln [(home_id, away_id), ...]
    """
    if len(teams) < 2:
        return []

    pairs = []
    for i in range(len(teams) // 2):
        home = teams[i]
        away = teams[-(i + 1)]
        pairs.append((home, away))

    return pairs


def apply_byes(teams: List[int]) -> List[Optional[int]]:
    """
    Fügt Freilose (None) hinzu um Bracket auf nächste Zweierpotenz zu bringen.

    Freilose werden VON UNTEN aufgefüllt:
    - 13 Teams → 16 (3 Freilose): teams[13], teams[14], teams[15] = None
    - 5 Teams → 8 (3 Freilose): teams[5], teams[6], teams[7] = None

    Args:
        teams: Liste von team_ids

    Returns:
        Aufgefüllte Liste mit None für Freilose
    """
    n = len(teams)
    bracket_size = _next_power_of_two(n)
    byes_needed = bracket_size - n

    # Freilose von unten auffüllen
    result = teams.copy()
    for _ in range(byes_needed):
        result.append(None)

    return result


def _next_power_of_two(n: int) -> int:
    """Berechnet nächste Zweierpotenz ≥ n."""
    if n <= 1:
        return 1
    return 1 << (n - 1).bit_length()


def generate_rounds(
    pairs: List[Tuple[Optional[int], Optional[int]]],
    bracket_id: int,
    season_id: int,
    bracket_type: str,
    db: Session
) -> List[models.KOMatch]:
    """
    Generiert alle KO-Runden und persistiert sie.

    Prozess:
    1. Berechne Anzahl Runden (log2 der Bracket-Größe)
    2. Erstelle ALLE Matches für ALLE Runden (Bracket-Persistenz)
    3. Verknüpfe Matches mit next_match_id/next_match_slot
    4. Befülle Runde 1 mit Teams
    5. Handle Freilose (away_team_id = None → Sieger direkt weiterleiten)

    Args:
        pairs: Paarungen für Runde 1 [(home, away), ...]
        bracket_id: ID des KOBracket
        season_id: ID der Saison
        bracket_type: "meister", "lucky_loser" oder "loser"
        db: SQLAlchemy Session

    Returns:
        Liste aller erstellten KOMatch Objekte
    """
    if not pairs:
        return []

    # Anzahl Runden berechnen
    bracket_size = len(pairs) * 2
    total_rounds = int(math.log2(bracket_size))

    # Alle Matches für alle Runden erstellen (von vorne nach hinten)
    all_matches = []

    for round_num in range(1, total_rounds + 1):
        matches_in_round = bracket_size // (2 ** round_num)
        for pos in range(1, matches_in_round + 1):
            match = models.KOMatch(
                season_id=season_id,
                bracket_type=bracket_type,
                round=round_num,
                position=pos,
                status="pending"
            )
            db.add(match)
            all_matches.append(match)

    db.flush()  # IDs generieren

    # Verknüpfungen setzen (Match → nächstes Match)
    for match in all_matches:
        if match.round < total_rounds:
            next_round = match.round + 1
            next_pos = (match.position + 1) // 2

            next_match = next(
                (m for m in all_matches if m.round == next_round and m.position == next_pos),
                None
            )

            if next_match:
                match.next_match_id = next_match.id
                # Gerade Position → away, Ungerade → home
                match.next_match_slot = "home" if match.position % 2 == 1 else "away"

    # Runde 1 befüllen
    round1_matches = sorted(
        [m for m in all_matches if m.round == 1],
        key=lambda m: m.position
    )

    for i, (home_id, away_id) in enumerate(pairs):
        if i >= len(round1_matches):
            break

        match = round1_matches[i]
        match.home_team_id = home_id
        match.away_team_id = away_id

        # Freilos-Handling
        if away_id is None:
            # Freilos: home_team steigt direkt auf
            match.is_bye = 1
            match.status = "played"

            # Sieger direkt in nächste Runde eintragen
            if match.next_match_id:
                next_match = db.get(models.KOMatch, match.next_match_id)
                if next_match:
                    if match.next_match_slot == "home":
                        next_match.home_team_id = home_id
                    else:
                        next_match.away_team_id = home_id
        else:
            # Normales Match
            match.status = "scheduled"

    return all_matches


def generate_ko_brackets(season_id: int, db: Session) -> Dict:
    """
    Haupt-Funktion: Generiert alle 3 KO-Brackets für eine Saison.

    Prozess:
    1. Qualifizierte Teams aus Gruppenphase ermitteln
    2. Für jeden bracket_type (meister, lucky_loser, loser):
       - KOBracket erstellen
       - Freilose hinzufügen
       - Teams seeden
       - Matches generieren
    3. Alles in DB persistieren

    Args:
        season_id: ID der Saison
        db: SQLAlchemy Session

    Returns:
        Dict mit Zusammenfassung pro Bracket:
        {
            "meister": {"bracket_id": X, "matches_count": Y, "rounds": Z},
            "lucky_loser": {...},
            "loser": {...}
        }

    Raises:
        ValueError: Wenn Gruppen nicht abgeschlossen oder bereits Brackets existieren
    """
    # Qualifizierte Teams ermitteln
    qualified = get_qualified_teams(season_id, db)

    result = {}

    for bracket_type in ["meister", "lucky_loser", "loser"]:
        teams = qualified[bracket_type]

        if not teams:
            # Kein Team für dieses Bracket (z.B. nur 2 Gruppen → keine 3. Plätze)
            result[bracket_type] = {
                "bracket_id": None,
                "matches_count": 0,
                "rounds": 0,
                "message": "Keine Teams für dieses Bracket"
            }
            continue

        # Prüfe ob Bracket bereits existiert
        existing = db.query(models.KOBracket).filter(
            models.KOBracket.season_id == season_id,
            models.KOBracket.bracket_type == bracket_type
        ).first()

        if existing:
            result[bracket_type] = {
                "bracket_id": existing.id,
                "matches_count": 0,
                "rounds": 0,
                "message": "Bracket bereits vorhanden (übersprungen)"
            }
            continue

        # KOBracket erstellen
        bracket = models.KOBracket(
            season_id=season_id,
            bracket_type=bracket_type,
            status="active",
            generated_at=datetime.utcnow()
        )
        db.add(bracket)
        db.flush()

        # Freilose hinzufügen
        teams_with_byes = apply_byes(teams)

        # Teams seeden
        pairs = seed_teams(teams_with_byes)

        # Runden generieren
        matches = generate_rounds(
            pairs=pairs,
            bracket_id=bracket.id,
            season_id=season_id,
            bracket_type=bracket_type,
            db=db
        )

        # Ergebnis zusammenfassen
        bracket_size = len(teams_with_byes)
        total_rounds = int(math.log2(bracket_size)) if bracket_size > 0 else 0

        result[bracket_type] = {
            "bracket_id": bracket.id,
            "matches_count": len(matches),
            "rounds": total_rounds,
            "teams_count": len(teams),
            "byes_count": bracket_size - len(teams)
        }

    db.commit()
    return result


# ============================================================
# TESTS
# ============================================================

if __name__ == "__main__":
    """
    Tests für die Bracket-Generierungs-Logik (ohne DB).
    """
    print("=" * 60)
    print("KO-BRACKET-GENERATOR TESTS")
    print("=" * 60)

    # Test 1: 16 Teams → 0 Freilose
    print("\n### Test 1: 16 Teams (0 Freilose)")
    teams_16 = list(range(1, 17))  # [1, 2, 3, ..., 16]
    teams_with_byes = apply_byes(teams_16)
    print(f"Original: {len(teams_16)} Teams")
    print(f"Mit Byes: {len(teams_with_byes)} Teams")
    print(f"Freilose: {teams_with_byes.count(None)}")
    print(f"Bracket-Größe: {_next_power_of_two(len(teams_16))}")

    pairs = seed_teams(teams_with_byes)
    print(f"\nPaarungen (erste 4):")
    for i, (home, away) in enumerate(pairs[:4], 1):
        print(f"  Match {i}: Team {home} vs Team {away}")

    expected_pairs = [
        (1, 16), (2, 15), (3, 14), (4, 13),
        (5, 12), (6, 11), (7, 10), (8, 9)
    ]
    assert pairs == expected_pairs, "Seeding-Fehler bei 16 Teams"
    print("✓ Seeding korrekt")

    # Test 2: 13 Teams → 3 Freilose
    print("\n### Test 2: 13 Teams (3 Freilose)")
    teams_13 = list(range(1, 14))  # [1, 2, 3, ..., 13]
    teams_with_byes = apply_byes(teams_13)
    print(f"Original: {len(teams_13)} Teams")
    print(f"Mit Byes: {len(teams_with_byes)} Teams")
    print(f"Freilose: {teams_with_byes.count(None)}")
    print(f"Bracket-Größe: {_next_power_of_two(len(teams_13))}")

    # Freilose sollten an Positionen 13, 14, 15 sein
    assert teams_with_byes[13] is None, "Freilos-Position falsch"
    assert teams_with_byes[14] is None, "Freilos-Position falsch"
    assert teams_with_byes[15] is None, "Freilos-Position falsch"
    print("✓ Freilose an korrekten Positionen (13, 14, 15)")

    pairs = seed_teams(teams_with_byes)
    print(f"\nPaarungen (alle 8):")
    for i, (home, away) in enumerate(pairs, 1):
        away_str = f"Team {away}" if away is not None else "FREILOS"
        print(f"  Match {i}: Team {home} vs {away_str}")

    # Erwartung: 1 vs None, 2 vs None, 3 vs None, 4 vs 13, 5 vs 12, ...
    assert pairs[0] == (1, None), "Freilos-Paarung 1 falsch"
    assert pairs[1] == (2, None), "Freilos-Paarung 2 falsch"
    assert pairs[2] == (3, None), "Freilos-Paarung 3 falsch"
    assert pairs[3] == (4, 13), "Paarung 4 falsch"
    print("✓ Freilose korrekt zugeteilt")

    # Test 3: 5 Teams → 3 Freilose
    print("\n### Test 3: 5 Teams (3 Freilose)")
    teams_5 = list(range(1, 6))  # [1, 2, 3, 4, 5]
    teams_with_byes = apply_byes(teams_5)
    print(f"Original: {len(teams_5)} Teams")
    print(f"Mit Byes: {len(teams_with_byes)} Teams")
    print(f"Freilose: {teams_with_byes.count(None)}")
    bracket_size = _next_power_of_two(len(teams_5))
    print(f"Bracket-Größe: {bracket_size}")
    assert bracket_size == 8, "Bracket-Größe falsch"

    pairs = seed_teams(teams_with_byes)
    print(f"\nPaarungen (alle 4):")
    for i, (home, away) in enumerate(pairs, 1):
        away_str = f"Team {away}" if away is not None else "FREILOS"
        print(f"  Match {i}: Team {home} vs {away_str}")

    # Test 4: Gespiegeltes Seeding (16 Teams mit Buchstaben)
    print("\n### Test 4: Gespiegeltes Seeding (A-P)")
    teams_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H',
                     'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']
    pairs_letters = seed_teams(teams_letters)
    print(f"Paarungen:")
    for i, (home, away) in enumerate(pairs_letters, 1):
        print(f"  Match {i}: {home} vs {away}")

    expected = [
        ('A', 'P'), ('B', 'O'), ('C', 'N'), ('D', 'M'),
        ('E', 'L'), ('F', 'K'), ('G', 'J'), ('H', 'I')
    ]
    assert pairs_letters == expected, "Seeding A-P falsch"
    print("✓ Gespiegeltes Seeding korrekt")

    # Test 5: Rundenanzahl-Berechnung
    print("\n### Test 5: Rundenanzahl-Berechnung")
    test_cases = [
        (2, 1),   # 2 Teams → 1 Runde (Finale)
        (4, 2),   # 4 Teams → 2 Runden (HF, Finale)
        (8, 3),   # 8 Teams → 3 Runden (VF, HF, Finale)
        (16, 4),  # 16 Teams → 4 Runden
        (13, 4),  # 13 Teams → 16 Bracket → 4 Runden
        (5, 3),   # 5 Teams → 8 Bracket → 3 Runden
    ]

    for team_count, expected_rounds in test_cases:
        teams = list(range(1, team_count + 1))
        teams_with_byes = apply_byes(teams)
        bracket_size = len(teams_with_byes)
        rounds = int(math.log2(bracket_size))
        print(f"  {team_count} Teams → Bracket {bracket_size} → {rounds} Runden", end="")
        assert rounds == expected_rounds, f"Rundenzahl falsch für {team_count} Teams"
        print(" ✓")

    print("\n" + "=" * 60)
    print("ALLE TESTS ERFOLGREICH!")
    print("=" * 60)
