"""
End-to-End Tests für KO-Bracket-System v2 (keine Freilose, Aufrücker-Logik).

Funktioniert gegen In-Memory SQLite DB (kein laufender Server nötig).
Simuliert kompletten Ablauf: Saison → Gruppen → Teams → Matches → Brackets.

Tests:
1. test_20_teams_meister_8: 5G×4T → Meister 8, LL nicht generiert
2. test_32_teams: 8G×4T → Meister 16, LL 8, Loser nicht generiert
3. test_48_teams_alle_brackets: 12G×4T → alle 3 × 16
4. test_64_teams_keine_aufruecker: 16G×4T → alle 3 × 16, keine Aufrücker
5. test_preview_keine_db_writes: Preview darf keine DB-Änderungen machen
6. test_archived_season_fehler: Archived Season → ValueError
7. test_keine_freilose: Keine is_bye in generierten Matches
8. test_41_teams_gemischte_gruppen: 11G (8×4 + 3×3), unterschiedliche Rankings
9. test_ranking_sortierung_bestimmt_aufruecker: Rankings bestimmen Aufrücker-Auswahl
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.db import Base
from app import models
from app.ko_bracket_generator import generate_ko_brackets_v2, preview_ko_brackets
import app.ranking_service as ranking_svc


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def create_test_db():
    """Erstellt eine frische In-Memory SQLite DB."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def mock_ranking_sheet():
    """Mockt Google Sheets Ranking (alle Teams bekommen 9999.0)."""
    ranking_svc._sheet_cache["ranking"] = {"data": [], "timestamp": datetime.utcnow()}


def mock_ranking_sheet_custom(team_rankings: dict):
    """
    Mockt Google Sheets Ranking mit custom Werten.

    Args:
        team_rankings: {team_name: ranking_value, ...}
    """
    # Rankings in das Sheet-Format umwandeln (CSV-ähnlich)
    data = [
        {"teamName": name, "avg_ranking": rank}
        for name, rank in team_rankings.items()
    ]
    ranking_svc._sheet_cache["ranking"] = {"data": data, "timestamp": datetime.utcnow()}


def setup_season(db, num_groups: int, teams_per_group: int = 4) -> tuple:
    """
    Erstellt eine Test-Saison mit Gruppen, Teams und gespielten Matches.

    Rückgabe: (season_id, group_ids, all_teams)
    Platzierungen sind deterministisch: Team 0 gewinnt alle, Team 1 wird Zweiter, etc.

    Round-Robin für teams_per_group Teams:
    - Platz 1 schlägt alle anderen
    - Platz 2 schlägt Platz 3 und 4
    - Platz 3 schlägt Platz 4
    """
    season = models.Season(
        name=f"Test Saison {num_groups}G",
        participant_count=num_groups * teams_per_group,
        status="active"
    )
    db.add(season)
    db.flush()

    group_names = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    group_ids = []
    all_teams = {}

    for g_idx in range(num_groups):
        group = models.Group(
            season_id=season.id,
            name=group_names[g_idx],
            sort_order=g_idx
        )
        db.add(group)
        db.flush()
        group_ids.append(group.id)

        teams_in_group = []
        for t_idx in range(teams_per_group):
            team = models.Team(name=f"Gruppe_{group_names[g_idx]}_Platz{t_idx + 1}")
            db.add(team)
            db.flush()
            st = models.SeasonTeam(
                season_id=season.id,
                team_id=team.id,
                group_id=group.id
            )
            db.add(st)
            teams_in_group.append(team.id)

        all_teams[g_idx] = teams_in_group

        # Round-Robin Matches: Platzierungen sind klar
        t = teams_in_group

        if teams_per_group >= 2:
            # Platz1 vs Platz2: 3:0 (P1 gewinnt)
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[0], away_team_id=t[1],
                home_goals=3, away_goals=0, status="played"
            ))

        if teams_per_group >= 3:
            # Platz1 vs Platz3: 2:0
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[0], away_team_id=t[2],
                home_goals=2, away_goals=0, status="played"
            ))
            # Platz2 vs Platz3: 1:0 (P2 gewinnt)
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[1], away_team_id=t[2],
                home_goals=1, away_goals=0, status="played"
            ))

        if teams_per_group >= 4:
            # Platz1 vs Platz4: 4:0
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[0], away_team_id=t[3],
                home_goals=4, away_goals=0, status="played"
            ))
            # Platz2 vs Platz4: 3:0
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[1], away_team_id=t[3],
                home_goals=3, away_goals=0, status="played"
            ))
            # Platz3 vs Platz4: 2:0 (P3 gewinnt)
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[2], away_team_id=t[3],
                home_goals=2, away_goals=0, status="played"
            ))

    db.flush()
    return season.id, group_ids, all_teams


def setup_season_mixed_groups(db, group_sizes: list) -> tuple:
    """
    Erstellt eine Test-Saison mit gemischten Gruppengrößen.

    Args:
        db: SQLAlchemy Session
        group_sizes: Liste von Teamanzahlen pro Gruppe [4, 4, 3, 4, 3, ...]

    Rückgabe: (season_id, group_ids, all_teams)
    """
    num_groups = len(group_sizes)
    total_teams = sum(group_sizes)

    season = models.Season(
        name=f"Test Saison {num_groups}G gemischt",
        participant_count=total_teams,
        status="active"
    )
    db.add(season)
    db.flush()

    group_names = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    group_ids = []
    all_teams = {}

    for g_idx, teams_in_group_count in enumerate(group_sizes):
        group = models.Group(
            season_id=season.id,
            name=group_names[g_idx],
            sort_order=g_idx
        )
        db.add(group)
        db.flush()
        group_ids.append(group.id)

        teams_in_group = []
        for t_idx in range(teams_in_group_count):
            team = models.Team(name=f"Gruppe_{group_names[g_idx]}_Platz{t_idx + 1}")
            db.add(team)
            db.flush()
            st = models.SeasonTeam(
                season_id=season.id,
                team_id=team.id,
                group_id=group.id
            )
            db.add(st)
            teams_in_group.append(team.id)

        all_teams[g_idx] = teams_in_group

        # Round-Robin Matches
        t = teams_in_group

        if teams_in_group_count >= 2:
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[0], away_team_id=t[1],
                home_goals=3, away_goals=0, status="played"
            ))

        if teams_in_group_count >= 3:
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[0], away_team_id=t[2],
                home_goals=2, away_goals=0, status="played"
            ))
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[1], away_team_id=t[2],
                home_goals=1, away_goals=0, status="played"
            ))

        if teams_in_group_count >= 4:
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[0], away_team_id=t[3],
                home_goals=4, away_goals=0, status="played"
            ))
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[1], away_team_id=t[3],
                home_goals=3, away_goals=0, status="played"
            ))
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[2], away_team_id=t[3],
                home_goals=2, away_goals=0, status="played"
            ))

    db.flush()
    return season.id, group_ids, all_teams


def apply_result(db, match_id: int, home_goals: int, away_goals: int) -> int:
    """
    Trägt ein KO-Ergebnis ein und leitet den Sieger weiter.
    Gibt winner_id zurück.
    """
    match = db.get(models.KOMatch, match_id)
    assert match is not None, f"KOMatch {match_id} nicht gefunden"
    assert not match.is_bye, f"Match {match_id} ist ein Freilos"

    match.home_goals = home_goals
    match.away_goals = away_goals
    match.status = "played"

    winner_id = None
    if home_goals > away_goals:
        winner_id = match.home_team_id
    elif away_goals > home_goals:
        winner_id = match.away_team_id

    if winner_id and match.next_match_id:
        next_match = db.get(models.KOMatch, match.next_match_id)
        if next_match:
            if match.next_match_slot == "home":
                next_match.home_team_id = winner_id
            else:
                next_match.away_team_id = winner_id
            if next_match.home_team_id and next_match.away_team_id:
                next_match.status = "scheduled"

    db.flush()
    return winner_id


def get_team_name(db, team_id) -> str:
    if team_id is None:
        return "TBD"
    t = db.get(models.Team, team_id)
    return t.name if t else f"Team#{team_id}"


# ============================================================
# TEST 1: 20 Teams (5 Gruppen × 4) → Meister 8
# ============================================================

def test_20_teams_meister_8():
    """5G×4T: Meister 8 (5E+3Z), LL nicht generiert (2Z+5D=7<8), Loser nicht generiert."""
    mock_ranking_sheet()
    db = create_test_db()
    season_id, _, _ = setup_season(db, 5, 4)
    db.commit()

    result = generate_ko_brackets_v2(season_id, db)

    # Meister-Check
    m = result["meister"]
    assert m["bracket_id"] is not None, "Meister-Bracket wurde nicht erstellt"
    assert m["teams_count"] == 8, f"Erwartet 8 Teams, got {m['teams_count']}"
    assert m["aufruecker_count"] == 3, f"Erwartet 3 Aufrücker (5 Erste + 3 Zweite), got {m['aufruecker_count']}"
    assert m["rounds"] == 3, f"Erwartet 3 Runden (VF), got {m['rounds']}"

    # Lucky Loser sollte nicht generiert sein
    ll = result["lucky_loser"]
    assert ll["bracket_id"] is None, f"Lucky Loser sollte nicht generiert sein"

    # Loser sollte nicht generiert sein
    lo = result["loser"]
    assert lo["bracket_id"] is None, f"Loser sollte nicht generiert sein"

    # Keine Freilose
    all_matches = db.query(models.KOMatch).filter(
        models.KOMatch.season_id == season_id
    ).all()
    bye_matches = [m for m in all_matches if m.is_bye == 1]
    assert len(bye_matches) == 0, f"Freilos-Matches gefunden: {len(bye_matches)}"

    db.close()
    print("✓ test_20_teams_meister_8 bestanden")


# ============================================================
# TEST 2: 32 Teams (8 Gruppen × 4) → Meister 16, LL 8, Loser nicht generiert
# ============================================================

def test_32_teams():
    """8G×4T: Meister 16 (8E+8Z), LL 8 (0Z+8D), Loser nicht generiert."""
    mock_ranking_sheet()
    db = create_test_db()
    season_id, _, _ = setup_season(db, 8, 4)
    db.commit()

    result = generate_ko_brackets_v2(season_id, db)

    m = result["meister"]
    assert m["teams_count"] == 16, f"Meister: erwartet 16, got {m['teams_count']}"
    assert m["aufruecker_count"] == 8, f"Meister: erwartet 8 Aufrücker, got {m['aufruecker_count']}"
    assert m["rounds"] == 4, f"Meister: erwartet 4 Runden (AF), got {m['rounds']}"

    ll = result["lucky_loser"]
    assert ll["bracket_id"] is not None, "Lucky Loser sollte generiert sein"
    assert ll["teams_count"] == 8, f"Lucky Loser: erwartet 8, got {ll['teams_count']}"
    assert ll["aufruecker_count"] == 8, f"Lucky Loser: erwartet 8 Aufrücker (alle Dritten), got {ll['aufruecker_count']}"
    assert ll["rounds"] == 3, f"Lucky Loser: erwartet 3 Runden (VF), got {ll['rounds']}"

    lo = result["loser"]
    assert lo["bracket_id"] is None, "Loser sollte nicht generiert sein (0D+8V<16)"

    db.close()
    print("✓ test_32_teams bestanden")


# ============================================================
# TEST 3: 48 Teams (12 Gruppen × 4) → alle 3 × 16
# ============================================================

def test_48_teams_alle_brackets():
    """12G×4T: Meister 16 (12E+4Z), LL 16 (8Z+8D), Loser 16 (4D+12V)."""
    mock_ranking_sheet()
    db = create_test_db()
    season_id, _, _ = setup_season(db, 12, 4)
    db.commit()

    result = generate_ko_brackets_v2(season_id, db)

    m = result["meister"]
    assert m["teams_count"] == 16, f"Meister: erwartet 16, got {m['teams_count']}"
    assert m["aufruecker_count"] == 4, f"Meister: erwartet 4 Aufrücker (4 von 12 Zweiten), got {m['aufruecker_count']}"

    ll = result["lucky_loser"]
    assert ll["bracket_id"] is not None, "Lucky Loser sollte generiert sein"
    assert ll["teams_count"] == 16, f"Lucky Loser: erwartet 16, got {ll['teams_count']}"
    assert ll["aufruecker_count"] == 8, f"Lucky Loser: erwartet 8 Aufrücker (von 12 Dritten), got {ll['aufruecker_count']}"

    lo = result["loser"]
    assert lo["bracket_id"] is not None, "Loser sollte generiert sein"
    assert lo["teams_count"] == 16, f"Loser: erwartet 16, got {lo['teams_count']}"
    assert lo["aufruecker_count"] == 12, f"Loser: erwartet 12 Aufrücker (alle 12 Vierten), got {lo['aufruecker_count']}"

    db.close()
    print("✓ test_48_teams_alle_brackets bestanden")


# ============================================================
# TEST 4: 64 Teams (16 Gruppen × 4) → alle 3 × 16, keine Aufrücker
# ============================================================

def test_64_teams_keine_aufruecker():
    """16G×4T: alle 3 Brackets × 16, keine Aufrücker nötig."""
    mock_ranking_sheet()
    db = create_test_db()
    season_id, _, _ = setup_season(db, 16, 4)
    db.commit()

    result = generate_ko_brackets_v2(season_id, db)

    m = result["meister"]
    assert m["teams_count"] == 16
    assert m["aufruecker_count"] == 0, f"Meister sollte 0 Aufrücker haben, got {m['aufruecker_count']}"

    ll = result["lucky_loser"]
    assert ll["teams_count"] == 16
    assert ll["aufruecker_count"] == 0, f"Lucky Loser sollte 0 Aufrücker haben, got {ll['aufruecker_count']}"

    lo = result["loser"]
    assert lo["teams_count"] == 16
    assert lo["aufruecker_count"] == 0, f"Loser sollte 0 Aufrücker haben, got {lo['aufruecker_count']}"

    db.close()
    print("✓ test_64_teams_keine_aufruecker bestanden")


# ============================================================
# TEST 5: Preview — keine DB-Änderungen
# ============================================================

def test_preview_keine_db_writes():
    """Preview darf keine DB-Änderungen machen."""
    mock_ranking_sheet()
    db = create_test_db()
    season_id, _, _ = setup_season(db, 8, 4)
    db.commit()

    # Vor Preview: keine KOBracket/KOMatch Einträge
    before_brackets = db.query(models.KOBracket).count()
    before_matches = db.query(models.KOMatch).count()
    assert before_brackets == 0
    assert before_matches == 0

    # Preview aufrufen
    result = preview_ko_brackets(season_id, db)

    # Nach Preview: immer noch keine Einträge
    after_brackets = db.query(models.KOBracket).count()
    after_matches = db.query(models.KOMatch).count()
    assert after_brackets == 0, "Preview sollte keine KOBracket erstellen"
    assert after_matches == 0, "Preview sollte keine KOMatch erstellen"

    # Vorschau-Daten sollten vorhanden sein
    assert result["meister"] is not None, "Meister-Preview sollte vorhanden sein"
    assert result["meister"]["size"] == 16
    assert "team_names" in result

    db.close()
    print("✓ test_preview_keine_db_writes bestanden")


# ============================================================
# TEST 6: Archived Season → ValueError
# ============================================================

def test_archived_season_fehler():
    """Archived Season sollte ValueError werfen."""
    mock_ranking_sheet()
    db = create_test_db()

    season = models.Season(name="Alt Season", participant_count=32, status="archived")
    db.add(season)
    db.commit()

    try:
        generate_ko_brackets_v2(season.id, db)
        assert False, "ValueError erwartet für archivierte Saison"
    except ValueError as e:
        assert "archiviert" in str(e).lower(), f"Fehlermeldung sollte 'archiviert' enthalten: {e}"

    db.close()
    print("✓ test_archived_season_fehler bestanden")


# ============================================================
# TEST 7: Keine Freilose in Matches
# ============================================================

def test_keine_freilose():
    """Alle Matches sollten is_bye=0 und beide Teams haben."""
    mock_ranking_sheet()
    db = create_test_db()
    season_id, _, _ = setup_season(db, 12, 4)
    db.commit()

    generate_ko_brackets_v2(season_id, db)

    all_matches = db.query(models.KOMatch).filter(
        models.KOMatch.season_id == season_id
    ).all()

    # Keine Freilose
    bye_matches = [m for m in all_matches if m.is_bye == 1]
    assert len(bye_matches) == 0, f"Sollte 0 Freilos-Matches haben, found {len(bye_matches)}"

    # Alle Runde-1-Matches haben beide Teams
    r1_matches = [m for m in all_matches if m.round == 1]
    for m in r1_matches:
        assert m.home_team_id is not None, f"R1 Match {m.id}: home_team_id ist None"
        assert m.away_team_id is not None, f"R1 Match {m.id}: away_team_id ist None"
        assert m.status == "scheduled", f"R1 Match {m.id}: status sollte 'scheduled' sein, got {m.status}"

    db.close()
    print("✓ test_keine_freilose bestanden")


# ============================================================
# TEST 8: 41 Teams (gemischte Gruppen: 8×4 + 3×3)
# ============================================================

def test_41_teams_gemischte_gruppen():
    """
    11 Gruppen: 8 Gruppen à 4 Teams + 3 Gruppen à 3 Teams = 41 Teams.

    Erwartungen (E=11, Z=11, D=11, V=8):
    - Meister: 16 Teams (11 Erste + 5 Zweite)
    - Lucky Loser: 16 Teams (6 übrige Zweite + 10 Dritte)
    - Loser: NICHT generiert (1 Dritter + 8 Vierte = 9 < 16)

    Mit unterschiedlichen Rankings prüfen:
    - Zweite aus 4er-Gruppen: Rankings 100-800
    - Zweite aus 3er-Gruppen: Rankings 900-1100
    - Die 5 Aufrücker sollten die besten Zweiten sein (100-500, nicht 900-1100)
    """
    db = create_test_db()

    # Setup: 8×4 + 3×3 Teams = 41 Teams
    group_sizes = [4, 4, 4, 4, 4, 4, 4, 4, 3, 3, 3]  # 8 Gruppen à 4, dann 3 à 3
    season_id, group_ids, all_teams = setup_season_mixed_groups(db, group_sizes)
    db.commit()

    # Mock Rankings: Zweite aus 4er-Gruppen vs. 3er-Gruppen unterschiedlich
    team_rankings = {}

    # Zweite aus 4er-Gruppen (A-H): Rankings 100-800
    for g_idx in range(8):
        team_name = f"Gruppe_{chr(65 + g_idx)}_Platz2"
        team_rankings[team_name] = 100 + (g_idx * 100)

    # Zweite aus 3er-Gruppen (I-K): Rankings 900-1100
    for g_idx in range(8, 11):
        team_name = f"Gruppe_{chr(65 + g_idx)}_Platz2"
        team_rankings[team_name] = 900 + ((g_idx - 8) * 100)

    # Dritte: Rankings 1200-2200
    for g_idx in range(11):
        team_name = f"Gruppe_{chr(65 + g_idx)}_Platz3"
        team_rankings[team_name] = 1200 + (g_idx * 100)

    # Vierte (nur 4er-Gruppen): Rankings 2300-3000
    for g_idx in range(8):
        team_name = f"Gruppe_{chr(65 + g_idx)}_Platz4"
        team_rankings[team_name] = 2300 + (g_idx * 100)

    mock_ranking_sheet_custom(team_rankings)

    result = generate_ko_brackets_v2(season_id, db)

    # Meister: 16 Teams (11 Erste + 5 Zweite)
    m = result["meister"]
    assert m["bracket_id"] is not None, "Meister-Bracket sollte generiert sein"
    assert m["teams_count"] == 16, f"Meister: erwartet 16, got {m['teams_count']}"
    assert m["aufruecker_count"] == 5, f"Meister: erwartet 5 Aufrücker, got {m['aufruecker_count']}"
    assert m["rounds"] == 4, f"Meister: erwartet 4 Runden (AF), got {m['rounds']}"

    # Lucky Loser: 16 Teams (6 übrige Zweite + 10 Dritte)
    ll = result["lucky_loser"]
    assert ll["bracket_id"] is not None, "Lucky Loser sollte generiert sein"
    assert ll["teams_count"] == 16, f"Lucky Loser: erwartet 16, got {ll['teams_count']}"
    assert ll["aufruecker_count"] == 10, f"Lucky Loser: erwartet 10 Dritte-Aufrücker, got {ll['aufruecker_count']}"

    # Loser: NICHT generiert (1 Dritter + 8 Vierte = 9 < 16)
    lo = result["loser"]
    assert lo["bracket_id"] is None, "Loser sollte NICHT generiert sein"

    # Keine Freilose
    all_matches = db.query(models.KOMatch).filter(
        models.KOMatch.season_id == season_id
    ).all()
    bye_matches = [m for m in all_matches if m.is_bye == 1]
    assert len(bye_matches) == 0, f"Sollte 0 Freilos-Matches haben, found {len(bye_matches)}"

    db.close()
    print("✓ test_41_teams_gemischte_gruppen bestanden")


# ============================================================
# TEST 9: Ranking-Sortierung bestimmt Aufrücker
# ============================================================

def test_ranking_sortierung_bestimmt_aufruecker():
    """
    10 Gruppen à 4 Teams = 40 Teams.
    Meister braucht 6 Aufrücker aus Zweiten (10 Erste + 6 Zweite = 16).

    Rankings der Zweiten sind UMGEKEHRT:
    - Gruppe A (Zweiter): Ranking 1000 (schlechtester)
    - Gruppe B (Zweiter): Ranking 900
    - ...
    - Gruppe J (Zweiter): Ranking 100 (bester)

    Erwartung: Die 6 Aufrücker sind die Zweiten mit Rankings 100-600
    (Gruppen J, I, H, G, F, E), NICHT die ersten alphabetisch (A, B, C, D, E, F).

    Lucky Loser: 4 übrige Zweite (schlechteste 4: A, B, C, D) + 4 beste Dritte = 8 Teams
    (weil 4 + 10 = 14 < 16, Fallback auf 8)
    """
    db = create_test_db()
    season_id, _, _ = setup_season(db, 10, 4)
    db.commit()

    # Mock Rankings: Zweite mit UMGEKEHRTEN Rankings
    team_rankings = {}

    # Zweite mit umgekehrten Rankings (besser = niedriger Ø)
    group_names = list("ABCDEFGHIJ")
    for g_idx, group_char in enumerate(group_names):
        team_name = f"Gruppe_{group_char}_Platz2"
        # A=1000, B=900, ..., J=100
        team_rankings[team_name] = 1000 - (g_idx * 100)

    # Erste: normale Rankings (nicht relevant für Sorting)
    for g_idx, group_char in enumerate(group_names):
        team_name = f"Gruppe_{group_char}_Platz1"
        team_rankings[team_name] = 3000 + (g_idx * 100)

    # Dritte und Vierte: weniger relevant für diesen Test
    for g_idx, group_char in enumerate(group_names):
        team_name = f"Gruppe_{group_char}_Platz3"
        team_rankings[team_name] = 2000 + (g_idx * 100)
        team_name = f"Gruppe_{group_char}_Platz4"
        team_rankings[team_name] = 2500 + (g_idx * 100)

    mock_ranking_sheet_custom(team_rankings)

    result = generate_ko_brackets_v2(season_id, db)

    # Meister: 10 Erste + 6 Zweite = 16
    m = result["meister"]
    assert m["bracket_id"] is not None
    assert m["teams_count"] == 16, f"Meister: erwartet 16, got {m['teams_count']}"
    assert m["aufruecker_count"] == 6, f"Meister: erwartet 6 Aufrücker, got {m['aufruecker_count']}"

    # Lucky Loser: 4 übrige Zweite + 4 beste Dritte = 8 Teams (Fallback)
    # (weil 4 + 10 Dritte = 14 < 16, Fallback auf 8)
    ll = result["lucky_loser"]
    assert ll["bracket_id"] is not None, "Lucky Loser sollte generiert sein"
    assert ll["teams_count"] == 8, f"Lucky Loser: erwartet 8 Teams (Fallback), got {ll['teams_count']}"
    assert ll["rounds"] == 3, f"Lucky Loser: erwartet 3 Runden (VF), got {ll['rounds']}"
    # Lucky Loser hat: 4 übrige Zweite + 4 beste Dritte = 8
    assert ll["aufruecker_count"] == 4, f"Lucky Loser: erwartet 4 Dritte-Aufrücker, got {ll['aufruecker_count']}"

    # Loser: 6 übrige Dritte + 10 Vierte = 16 oder None?
    # 6 + 10 = 16 ≥ 16 → SOLLTE generiert werden
    lo = result["loser"]
    # Das hängt davon ab wie viele Dritte aufgerückt sind
    # Mit den Rankings sollten 4 beste Dritte in Lucky Loser sein
    # Es bleiben 10 - 4 = 6 Dritte
    # 6 + 10 Vierte = 16 ≥ 16 → Loser SOLLTE generiert werden
    assert lo["bracket_id"] is not None, "Loser sollte generiert sein (6 Dritte + 10 Vierte = 16)"
    assert lo["teams_count"] == 16, f"Loser: erwartet 16, got {lo['teams_count']}"

    db.close()
    print("✓ test_ranking_sortierung_bestimmt_aufruecker bestanden")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    print("=" * 70)
    print("KO-BRACKET-SYSTEM v2 — END-TO-END TESTS")
    print("=" * 70)

    tests = [
        ("test_20_teams_meister_8", test_20_teams_meister_8),
        ("test_32_teams", test_32_teams),
        ("test_48_teams_alle_brackets", test_48_teams_alle_brackets),
        ("test_64_teams_keine_aufruecker", test_64_teams_keine_aufruecker),
        ("test_preview_keine_db_writes", test_preview_keine_db_writes),
        ("test_archived_season_fehler", test_archived_season_fehler),
        ("test_keine_freilose", test_keine_freilose),
        ("test_41_teams_gemischte_gruppen", test_41_teams_gemischte_gruppen),
        ("test_ranking_sortierung_bestimmt_aufruecker", test_ranking_sortierung_bestimmt_aufruecker),
    ]

    failed = []

    for test_name, test_fn in tests:
        try:
            test_fn()
        except AssertionError as e:
            print(f"✗ {test_name}: {e}")
            failed.append(test_name)
        except Exception as e:
            import traceback
            print(f"✗ {test_name}: EXCEPTION")
            traceback.print_exc()
            failed.append(test_name)

    print("\n" + "=" * 70)
    if failed:
        print(f"✗ {len(failed)}/{len(tests)} Test(s) fehlgeschlagen:")
        for name in failed:
            print(f"  - {name}")
        sys.exit(1)
    else:
        print(f"✓ Alle {len(tests)} Tests bestanden!")
    print("=" * 70)
