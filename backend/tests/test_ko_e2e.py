"""
End-to-End Test für das KO-Bracket-System.

Arbeitet direkt gegen eine In-Memory SQLite DB (kein laufender Server nötig).
Simuliert den kompletten Ablauf: Saison → Gruppen → Teams → Matches → Brackets → Sieger-Weiterleitung.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app import models
from app.ko_bracket_generator import generate_ko_brackets


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def create_test_db():
    """Erstellt eine frische In-Memory SQLite DB."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def setup_season(db, num_groups: int, teams_per_group: int = 3) -> tuple:
    """
    Erstellt eine Test-Saison mit Gruppen, Teams und gespielten Matches.

    Rückgabe: (season_id, group_ids)
    Platzierungen sind deterministisch: Team 0 gewinnt alle, Team 1 wird Zweiter, Team 2 Dritter.
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
    all_teams = {}  # group_idx -> [team_id_platz1, team_id_platz2, team_id_platz3]

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

        # Round-Robin Matches: Jedes Team gegen jedes andere (klare Platzierungen)
        # Platz1 schlägt alle, Platz2 schlägt Platz3
        t = teams_in_group
        if teams_per_group >= 2:
            # Platz1 vs Platz2: 3:0
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
            # Platz2 vs Platz3: 1:0
            db.add(models.Match(
                season_id=season.id, group_id=group.id,
                home_team_id=t[1], away_team_id=t[2],
                home_goals=1, away_goals=0, status="played"
            ))

    db.flush()
    return season.id, group_ids, all_teams


def apply_result(db, match_id: int, home_goals: int, away_goals: int) -> int:
    """
    Trägt ein KO-Ergebnis ein und leitet den Sieger weiter (identisch zu PATCH /ko-matches/{id}).
    Gibt winner_id zurück.
    """
    match = db.get(models.KOMatch, match_id)
    assert match is not None, f"KOMatch {match_id} nicht gefunden"
    assert not match.is_bye, f"Match {match_id} ist ein Freilos – kann kein Ergebnis eingetragen werden"

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


def print_bracket(db, season_id: int, bracket_type: str):
    """Gibt den Bracket-Baum als Text aus."""
    matches = (
        db.query(models.KOMatch)
        .filter(
            models.KOMatch.season_id == season_id,
            models.KOMatch.bracket_type == bracket_type
        )
        .order_by(models.KOMatch.round, models.KOMatch.position)
        .all()
    )

    max_round = max(m.round for m in matches)
    round_names = {1: "Runde 1", 2: "Runde 2", 3: "Runde 3", 4: "Runde 4"}
    if max_round == 4:
        round_names = {1: "Achtelfinale", 2: "Viertelfinale", 3: "Halbfinale", 4: "Finale"}
    elif max_round == 3:
        round_names = {1: "Viertelfinale", 2: "Halbfinale", 3: "Finale"}
    elif max_round == 2:
        round_names = {1: "Halbfinale", 2: "Finale"}
    elif max_round == 1:
        round_names = {1: "Finale"}

    for r in range(1, max_round + 1):
        round_matches = [m for m in matches if m.round == r]
        print(f"\n{round_names.get(r, f'Runde {r}')}:")
        for m in sorted(round_matches, key=lambda x: x.position):
            home = get_team_name(db, m.home_team_id)
            away = get_team_name(db, m.away_team_id)
            score = f"{m.home_goals}:{m.away_goals}" if m.home_goals is not None else "   "
            bye = " [BYE]" if m.is_bye else ""
            next_info = f"→ next=#{m.next_match_id}/{m.next_match_slot}" if m.next_match_id else "→ [ENDE]"
            print(f"  P{m.position} id={m.id}: {home} ({score}) {away}{bye}  status={m.status}  {next_info}")


# ============================================================
# SIEGER-VALIDIERUNG
# ============================================================

def validate_round_advancement(db, season_id: int, bracket_type: str, completed_round: int):
    """
    Nach dem Spielen von Runde N prüfen ob alle Sieger korrekt in Runde N+1 eingetragen sind.
    """
    matches_r = (
        db.query(models.KOMatch)
        .filter(
            models.KOMatch.season_id == season_id,
            models.KOMatch.bracket_type == bracket_type,
            models.KOMatch.round == completed_round
        )
        .all()
    )

    errors = []
    for m in matches_r:
        if m.is_bye:
            # Bye: home_team muss ins next_match eingetragen sein
            if m.next_match_id:
                nm = db.get(models.KOMatch, m.next_match_id)
                expected_id = m.home_team_id
                actual_id = nm.home_team_id if m.next_match_slot == "home" else nm.away_team_id
                if actual_id != expected_id:
                    errors.append(
                        f"BYE Match P{m.position}: erwartet {get_team_name(db, expected_id)} "
                        f"in next_match {m.next_match_id}/{m.next_match_slot}, "
                        f"aber dort steht {get_team_name(db, actual_id)}"
                    )
            continue

        if m.status != "played":
            continue  # noch nicht gespielt, überspringen

        winner_id = None
        if m.home_goals is not None and m.away_goals is not None:
            if m.home_goals > m.away_goals:
                winner_id = m.home_team_id
            elif m.away_goals > m.home_goals:
                winner_id = m.away_team_id

        if winner_id is None:
            continue  # Unentschieden, keine Auto-Weiterleitung

        if not m.next_match_id:
            continue  # Finale, kein next_match

        nm = db.get(models.KOMatch, m.next_match_id)
        actual_id = nm.home_team_id if m.next_match_slot == "home" else nm.away_team_id

        if actual_id != winner_id:
            errors.append(
                f"Match R{m.round}P{m.position} id={m.id}: "
                f"Sieger {get_team_name(db, winner_id)} sollte in next_match "
                f"#{m.next_match_id}/{m.next_match_slot} stehen, "
                f"aber dort steht {get_team_name(db, actual_id)}"
            )

    return errors


# ============================================================
# TEST 1: Perfekte 16 Gruppen
# ============================================================

def test_perfekte_16():
    print("\n" + "=" * 60)
    print("=== Test 1: Perfekte 16 (16 Gruppen, 0 Byes) ===")
    print("=" * 60)

    db = create_test_db()
    season_id, group_ids, all_teams = setup_season(db, num_groups=16, teams_per_group=3)
    db.commit()

    result = generate_ko_brackets(season_id, db)

    # Bracket-Check
    m_result = result["meister"]
    assert m_result["bracket_id"] is not None, "Meister-Bracket wurde nicht erstellt"
    assert m_result["teams_count"] == 16, f"Erwartet 16 Teams, got {m_result['teams_count']}"
    assert m_result["byes_count"] == 0, f"Erwartet 0 Byes, got {m_result['byes_count']}"
    assert m_result["rounds"] == 4, f"Erwartet 4 Runden, got {m_result['rounds']}"
    assert m_result["matches_count"] == 15, f"Erwartet 15 Matches, got {m_result['matches_count']}"

    r1_matches = (
        db.query(models.KOMatch)
        .filter(
            models.KOMatch.season_id == season_id,
            models.KOMatch.bracket_type == "meister",
            models.KOMatch.round == 1
        )
        .order_by(models.KOMatch.position)
        .all()
    )
    assert len(r1_matches) == 8, f"Erwartet 8 R1-Matches, got {len(r1_matches)}"

    # Seeding prüfen: Position 1 = Gruppe_A_Platz1 vs Gruppe_P_Platz1
    p1_home = get_team_name(db, r1_matches[0].home_team_id)
    p1_away = get_team_name(db, r1_matches[0].away_team_id)
    assert p1_home == "Gruppe_A_Platz1", f"R1P1 home: erwartet Gruppe_A_Platz1, got {p1_home}"
    assert p1_away == "Gruppe_P_Platz1", f"R1P1 away: erwartet Gruppe_P_Platz1, got {p1_away}"
    print(f"✓ Seeding korrekt: R1P1 = {p1_home} vs {p1_away}")

    p8_home = get_team_name(db, r1_matches[7].home_team_id)
    p8_away = get_team_name(db, r1_matches[7].away_team_id)
    assert p8_home == "Gruppe_H_Platz1", f"R1P8 home: erwartet Gruppe_H_Platz1, got {p8_home}"
    assert p8_away == "Gruppe_I_Platz1", f"R1P8 away: erwartet Gruppe_I_Platz1, got {p8_away}"
    print(f"✓ Seeding korrekt: R1P8 = {p8_home} vs {p8_away}")

    print_bracket(db, season_id, "meister")

    # Alle Runden durchspielen
    print("\n--- Spiele Runde 1 ---")
    for m in sorted(r1_matches, key=lambda x: x.position):
        winner_id = apply_result(db, m.id, 2, 0)
        winner = get_team_name(db, winner_id)
        home = get_team_name(db, m.home_team_id)
        away = get_team_name(db, m.away_team_id)
        next_info = f"weiter als {m.next_match_slot.upper()} zu R2P{(m.position + 1) // 2}" if m.next_match_id else ""
        print(f"  P{m.position}: {home} (2:0) {away} → Sieger: {winner} → {next_info}")

    errors = validate_round_advancement(db, season_id, "meister", 1)
    assert not errors, "Fehler nach Runde 1:\n" + "\n".join(errors)
    print("✓ Alle Sieger aus Runde 1 korrekt weitergeleitet")

    for rnd in [2, 3]:
        rnd_matches = (
            db.query(models.KOMatch)
            .filter(
                models.KOMatch.season_id == season_id,
                models.KOMatch.bracket_type == "meister",
                models.KOMatch.round == rnd
            )
            .order_by(models.KOMatch.position)
            .all()
        )
        print(f"\n--- Spiele Runde {rnd} ---")
        for m in rnd_matches:
            assert m.home_team_id is not None, f"R{rnd}P{m.position}: home_team fehlt!"
            assert m.away_team_id is not None, f"R{rnd}P{m.position}: away_team fehlt!"
            winner_id = apply_result(db, m.id, 1, 0)
            winner = get_team_name(db, winner_id)
            home = get_team_name(db, m.home_team_id)
            away = get_team_name(db, m.away_team_id)
            next_info = f"→ R{rnd + 1}P{(m.position + 1) // 2}" if m.next_match_id else ""
            print(f"  P{m.position}: {home} vs {away} → Sieger: {winner} {next_info}")

        errors = validate_round_advancement(db, season_id, "meister", rnd)
        assert not errors, f"Fehler nach Runde {rnd}:\n" + "\n".join(errors)
        print(f"✓ Alle Sieger aus Runde {rnd} korrekt weitergeleitet")

    # Finale
    finale = (
        db.query(models.KOMatch)
        .filter(
            models.KOMatch.season_id == season_id,
            models.KOMatch.bracket_type == "meister",
            models.KOMatch.round == 4
        )
        .first()
    )
    assert finale is not None, "Finale nicht gefunden"
    assert finale.home_team_id is not None, "Finale: home_team fehlt"
    assert finale.away_team_id is not None, "Finale: away_team fehlt"
    home_f = get_team_name(db, finale.home_team_id)
    away_f = get_team_name(db, finale.away_team_id)
    print(f"\n--- Finale ---")
    print(f"  FINALE: {home_f} vs {away_f}")
    winner_id = apply_result(db, finale.id, 3, 1)
    print(f"  Turniersieger: {get_team_name(db, winner_id)}")

    db.close()
    print("\n✓ Test 1 bestanden")


# ============================================================
# TEST 2: 12 Gruppen (nicht-Zweierpotenz, 4 Byes)
# ============================================================

def test_12_gruppen():
    print("\n" + "=" * 60)
    print("=== Test 2: 12 Gruppen (→ 16er Bracket, 4 Byes) ===")
    print("=" * 60)

    db = create_test_db()
    season_id, group_ids, all_teams = setup_season(db, num_groups=12, teams_per_group=3)
    db.commit()

    result = generate_ko_brackets(season_id, db)

    m_result = result["meister"]
    assert m_result["bracket_id"] is not None
    assert m_result["teams_count"] == 12, f"Erwartet 12 Teams, got {m_result['teams_count']}"
    assert m_result["byes_count"] == 4, f"Erwartet 4 Byes, got {m_result['byes_count']}"
    assert m_result["rounds"] == 4, f"Erwartet 4 Runden, got {m_result['rounds']}"
    print(f"✓ 12 Teams + 4 Byes → 16er Bracket, 4 Runden")

    r1_matches = (
        db.query(models.KOMatch)
        .filter(
            models.KOMatch.season_id == season_id,
            models.KOMatch.bracket_type == "meister",
            models.KOMatch.round == 1
        )
        .order_by(models.KOMatch.position)
        .all()
    )

    bye_matches = [m for m in r1_matches if m.is_bye]
    normal_matches = [m for m in r1_matches if not m.is_bye]
    print(f"✓ Runde 1: {len(normal_matches)} normale Matches + {len(bye_matches)} Freilose")
    assert len(bye_matches) == 4, f"Erwartet 4 Bye-Matches, got {len(bye_matches)}"

    # Freilos-Teams müssen in Runde 2 stehen
    for m in bye_matches:
        assert m.next_match_id is not None, f"Bye-Match P{m.position} hat kein next_match_id!"
        nm = db.get(models.KOMatch, m.next_match_id)
        actual = nm.home_team_id if m.next_match_slot == "home" else nm.away_team_id
        assert actual == m.home_team_id, (
            f"Bye P{m.position}: {get_team_name(db, m.home_team_id)} sollte in "
            f"R2/{m.next_match_slot} stehen, aber dort ist {get_team_name(db, actual)}"
        )

    print("✓ Alle 4 Bye-Teams korrekt in Runde 2 eingetragen")

    print_bracket(db, season_id, "meister")

    # Alle normalen R1-Matches spielen
    print("\n--- Spiele Runde 1 (normale Matches) ---")
    for m in sorted(normal_matches, key=lambda x: x.position):
        winner_id = apply_result(db, m.id, 2, 1)
        home = get_team_name(db, m.home_team_id)
        away = get_team_name(db, m.away_team_id)
        print(f"  P{m.position}: {home} (2:1) {away} → Sieger: {get_team_name(db, winner_id)}")

    errors = validate_round_advancement(db, season_id, "meister", 1)
    assert not errors, "Fehler nach Runde 1:\n" + "\n".join(errors)
    print("✓ Alle Sieger aus Runde 1 korrekt weitergeleitet")

    # Runde 2: alle müssen besetzt sein
    r2_matches = (
        db.query(models.KOMatch)
        .filter(
            models.KOMatch.season_id == season_id,
            models.KOMatch.bracket_type == "meister",
            models.KOMatch.round == 2
        )
        .order_by(models.KOMatch.position)
        .all()
    )
    print(f"\n--- Runde 2 ({len(r2_matches)} Matches) ---")
    for m in r2_matches:
        home = get_team_name(db, m.home_team_id)
        away = get_team_name(db, m.away_team_id)
        assert m.home_team_id is not None, f"R2P{m.position}: home_team fehlt!"
        assert m.away_team_id is not None, f"R2P{m.position}: away_team fehlt!"
        print(f"  P{m.position}: {home} vs {away}")
    print("✓ Runde 2 vollständig besetzt")

    # Restliche Runden durchspielen
    for rnd in [2, 3]:
        rnd_matches = (
            db.query(models.KOMatch)
            .filter(
                models.KOMatch.season_id == season_id,
                models.KOMatch.bracket_type == "meister",
                models.KOMatch.round == rnd
            )
            .order_by(models.KOMatch.position)
            .all()
        )
        for m in rnd_matches:
            apply_result(db, m.id, 2, 0)
        errors = validate_round_advancement(db, season_id, "meister", rnd)
        assert not errors, f"Fehler nach Runde {rnd}:\n" + "\n".join(errors)
        print(f"✓ Runde {rnd} gespielt, Sieger korrekt weitergeleitet")

    finale = (
        db.query(models.KOMatch)
        .filter(
            models.KOMatch.season_id == season_id,
            models.KOMatch.bracket_type == "meister",
            models.KOMatch.round == 4
        )
        .first()
    )
    assert finale.home_team_id and finale.away_team_id, "Finale nicht vollständig besetzt"
    winner_id = apply_result(db, finale.id, 2, 1)
    print(f"\n  FINALE: {get_team_name(db, finale.home_team_id)} vs {get_team_name(db, finale.away_team_id)}")
    print(f"  Turniersieger: {get_team_name(db, winner_id)}")

    db.close()
    print("\n✓ Test 2 bestanden")


# ============================================================
# TEST 3: Minimal – 4 Gruppen
# ============================================================

def test_minimal_4():
    print("\n" + "=" * 60)
    print("=== Test 3: Minimal – 4 Gruppen (HF + Finale) ===")
    print("=" * 60)

    db = create_test_db()
    season_id, group_ids, all_teams = setup_season(db, num_groups=4, teams_per_group=3)
    db.commit()

    result = generate_ko_brackets(season_id, db)

    m_result = result["meister"]
    assert m_result["teams_count"] == 4
    assert m_result["byes_count"] == 0
    assert m_result["rounds"] == 2
    assert m_result["matches_count"] == 3
    print(f"✓ 4 Teams → 2er Bracket, 2 Runden, 3 Matches (2x HF + Finale)")

    # Seeding: Gruppe_A_Platz1 vs Gruppe_D_Platz1, Gruppe_B_Platz1 vs Gruppe_C_Platz1
    r1_matches = (
        db.query(models.KOMatch)
        .filter(
            models.KOMatch.season_id == season_id,
            models.KOMatch.bracket_type == "meister",
            models.KOMatch.round == 1
        )
        .order_by(models.KOMatch.position)
        .all()
    )
    assert len(r1_matches) == 2

    p1_home = get_team_name(db, r1_matches[0].home_team_id)
    p1_away = get_team_name(db, r1_matches[0].away_team_id)
    p2_home = get_team_name(db, r1_matches[1].home_team_id)
    p2_away = get_team_name(db, r1_matches[1].away_team_id)
    print(f"✓ HF1: {p1_home} vs {p1_away}")
    print(f"✓ HF2: {p2_home} vs {p2_away}")
    assert p1_home == "Gruppe_A_Platz1"
    assert p1_away == "Gruppe_D_Platz1"
    assert p2_home == "Gruppe_B_Platz1"
    assert p2_away == "Gruppe_C_Platz1"

    print_bracket(db, season_id, "meister")

    # Halbfinale
    print("\n--- Halbfinale ---")
    for m in sorted(r1_matches, key=lambda x: x.position):
        winner_id = apply_result(db, m.id, 1, 0)
        home = get_team_name(db, m.home_team_id)
        away = get_team_name(db, m.away_team_id)
        slot = m.next_match_slot.upper() if m.next_match_slot else ""
        print(f"  P{m.position}: {home} (1:0) {away} → Sieger: {get_team_name(db, winner_id)} → {slot} im Finale")

    errors = validate_round_advancement(db, season_id, "meister", 1)
    assert not errors, "Fehler nach Halbfinale:\n" + "\n".join(errors)
    print("✓ Beide Halbfinale-Sieger korrekt ins Finale weitergeleitet")

    # Finale
    finale = (
        db.query(models.KOMatch)
        .filter(
            models.KOMatch.season_id == season_id,
            models.KOMatch.bracket_type == "meister",
            models.KOMatch.round == 2
        )
        .first()
    )
    assert finale.home_team_id is not None, "Finale: home_team fehlt"
    assert finale.away_team_id is not None, "Finale: away_team fehlt"
    home_f = get_team_name(db, finale.home_team_id)
    away_f = get_team_name(db, finale.away_team_id)
    print(f"\n--- Finale ---")
    print(f"  FINALE: {home_f} vs {away_f}")
    winner_id = apply_result(db, finale.id, 2, 0)
    print(f"  Turniersieger: {get_team_name(db, winner_id)}")

    db.close()
    print("\n✓ Test 3 bestanden")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    failed = []

    for test_fn in [test_perfekte_16, test_12_gruppen, test_minimal_4]:
        try:
            test_fn()
        except AssertionError as e:
            print(f"\n✗ FEHLGESCHLAGEN: {e}")
            failed.append(test_fn.__name__)
        except Exception as e:
            import traceback
            print(f"\n✗ EXCEPTION in {test_fn.__name__}:")
            traceback.print_exc()
            failed.append(test_fn.__name__)

    print("\n" + "=" * 60)
    if failed:
        print(f"✗ {len(failed)} Test(s) fehlgeschlagen: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("✓ Alle 3 Tests bestanden")
    print("=" * 60)
