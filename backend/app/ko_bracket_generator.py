"""
KO-Bracket-Generierung für 3-Bracket-System (v2).

Neue Logik v2 (seit 08.03.2026):
- KEINE Freilose mehr — Brackets haben exakt 8 oder 16 Teams
- Fehlende Slots werden mit Aufrückern aus niedrigeren Platzierungen gefüllt
- Aufrücker werden nach Onlineliga-Ranking sortiert (niedrigerer Ø = besser)

Brackets:
- Meisterrunde: Gruppenerste + Aufrücker aus Zweiten
- Lucky Loser: übrige Zweite + Aufrücker aus Dritten
- Loser: übrige Dritte + Aufrücker aus Vierten (optional)

Gilt NUR für nicht-archivierte Saisons.
"""

from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import math

from . import models
from .ranking_service import get_team_ranking


def get_qualified_teams_v2(season_id: int, db: Session) -> Dict:
    """
    Ermittelt Team-Pools für alle drei Brackets nach v2-Logik.

    KEINE Freilose. Aufrücker nach Onlineliga-Ranking.
    Gilt NUR für nicht-archivierte Saisons.

    Args:
        season_id: ID der Saison
        db: SQLAlchemy Session

    Returns:
        {
            "meister": [team_id, ...],          # 8 oder 16 Teams
            "lucky_loser": [team_id, ...],      # 8 oder 16 Teams, oder None
            "loser": [team_id, ...],            # 16 Teams, oder None
            "aufruecker_info": {
                "meister": [team_ids],          # Subset von meister die Aufrücker sind
                "lucky_loser": [team_ids],
                "loser": [team_ids]
            }
        }

    Raises:
        ValueError: wenn Season archived, Gruppen nicht abgeschlossen,
                    oder nicht genug Teams für Meisterrunde
    """
    # 1. Season-Status prüfen
    season = db.get(models.Season, season_id)
    if not season:
        raise ValueError(f"Season {season_id} nicht gefunden")
    if season.status == "archived":
        raise ValueError("KO-Brackets können nicht für archivierte Saisons generiert werden")

    # 2. Gruppen laden (sortiert nach name → A, B, C...) + Abschluss prüfen
    groups = db.query(models.Group).filter(
        models.Group.season_id == season_id
    ).order_by(models.Group.name).all()

    if not groups:
        raise ValueError(f"Keine Gruppen für Season {season_id} gefunden")

    for group in groups:
        matches = db.query(models.Match).filter(
            models.Match.group_id == group.id
        ).all()

        if not matches:
            raise ValueError(f"Gruppe {group.name} hat keine Matches")

        unplayed = [m for m in matches if m.status != "played"]
        if unplayed:
            raise ValueError(
                f"Gruppe {group.name} nicht abgeschlossen: "
                f"{len(unplayed)} Matches noch nicht gespielt"
            )

    # 3. Plätze 1–4 extrahieren (sortiert nach Gruppenname A, B, C...)
    erste_ids = []   # team_ids in Gruppenname-Reihenfolge
    zweite = []
    dritte = []
    vierte = []

    for group in groups:  # bereits nach name sortiert
        standings = _calculate_group_standings(group.id, db)
        if len(standings) >= 1:
            erste_ids.append(standings[0]["team_id"])
        if len(standings) >= 2:
            zweite.append(standings[1]["team_id"])
        if len(standings) >= 3:
            dritte.append(standings[2]["team_id"])
        if len(standings) >= 4:
            vierte.append(standings[3]["team_id"])

    # 4. Hilfsfunktion: team_ids nach Ranking sortieren (niedrigerer Wert = besser)
    def sort_by_ranking(team_ids: List[int]) -> List[int]:
        """Sortiert Teams nach Onlineliga-Ranking (niedrigerer Ø = besser)."""
        scored = []
        for tid in team_ids:
            team = db.get(models.Team, tid)
            name = team.name if team else ""
            score = get_team_ranking(name, db)
            scored.append((score, tid))
        scored.sort(key=lambda x: x[0])  # aufsteigend
        return [tid for _, tid in scored]

    # 5. SCHRITT 1 — Meisterrunde
    meister_aufruecker = []
    zweite_fuer_lucky = []

    if len(erste_ids) >= 16:
        # Zu viele Erste: best 16 nach Ranking
        sorted_erste = sort_by_ranking(erste_ids)
        meister_teams = sorted_erste[:16]
        # übrige Erste + alle Zweite in Lucky Loser pool
        zweite_fuer_lucky = sorted_erste[16:] + zweite
    else:
        zweite_sorted = sort_by_ranking(zweite)
        bedarf_16 = 16 - len(erste_ids)

        if len(erste_ids) + len(zweite_sorted) >= 16:
            # Normalfall: Zweite reichen zum Auffüllen auf 16
            meister_aufruecker = zweite_sorted[:bedarf_16]
            meister_teams = erste_ids + meister_aufruecker
            zweite_fuer_lucky = zweite_sorted[bedarf_16:]
        else:
            # FALLBACK auf 8er-Bracket
            if len(erste_ids) >= 8:
                meister_teams = erste_ids[:8]
                zweite_fuer_lucky = erste_ids[8:] + zweite_sorted
            else:
                bedarf_8 = 8 - len(erste_ids)
                if bedarf_8 <= len(zweite_sorted):
                    meister_aufruecker = zweite_sorted[:bedarf_8]
                    meister_teams = erste_ids + meister_aufruecker
                    zweite_fuer_lucky = zweite_sorted[bedarf_8:]
                else:
                    raise ValueError(
                        f"Nicht genug Teams für Meisterrunde (min. 8 benötigt). "
                        f"Verfügbar: {len(erste_ids)} Erste + {len(zweite_sorted)} Zweite = "
                        f"{len(erste_ids) + len(zweite_sorted)}"
                    )

    # 6. SCHRITT 2 — Lucky Loser
    dritte_sorted = sort_by_ranking(dritte)
    lucky_loser_aufruecker = []
    dritte_fuer_loser = dritte_sorted
    lucky_loser_teams = None

    bedarf_16_ll = 16 - len(zweite_fuer_lucky)

    if len(zweite_fuer_lucky) + len(dritte_sorted) >= 16:
        lucky_loser_aufruecker = dritte_sorted[:bedarf_16_ll]
        lucky_loser_teams = zweite_fuer_lucky + lucky_loser_aufruecker
        dritte_fuer_loser = dritte_sorted[bedarf_16_ll:]
    else:
        # FALLBACK auf 8er-Bracket
        bedarf_8_ll = 8 - len(zweite_fuer_lucky)
        if bedarf_8_ll <= 0:
            lucky_loser_teams = zweite_fuer_lucky[:8]
            dritte_fuer_loser = dritte_sorted
        elif bedarf_8_ll <= len(dritte_sorted):
            lucky_loser_aufruecker = dritte_sorted[:bedarf_8_ll]
            lucky_loser_teams = zweite_fuer_lucky + lucky_loser_aufruecker
            dritte_fuer_loser = dritte_sorted[bedarf_8_ll:]
        else:
            # Nicht genug für 8er-Bracket → nicht generiert
            lucky_loser_teams = None
            dritte_fuer_loser = dritte_sorted

    # 7. SCHRITT 3 — Loser (NUR 16, KEIN 8er-Fallback)
    vierte_sorted = sort_by_ranking(vierte)
    loser_aufruecker = []
    loser_teams = None

    if len(dritte_fuer_loser) + len(vierte_sorted) >= 16:
        bedarf_16_loser = 16 - len(dritte_fuer_loser)
        loser_aufruecker = vierte_sorted[:bedarf_16_loser]
        loser_teams = dritte_fuer_loser + loser_aufruecker
    # else: NICHT GENERIERT (kein 8er-Fallback für Loser)

    return {
        "meister": meister_teams,
        "lucky_loser": lucky_loser_teams,   # None wenn nicht generiert
        "loser": loser_teams,               # None wenn nicht generiert
        "aufruecker_info": {
            "meister": meister_aufruecker,
            "lucky_loser": lucky_loser_aufruecker,
            "loser": loser_aufruecker,
        }
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


def generate_rounds(
    pairs: List[Tuple[int, int]],
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

    Hinweis: KEINE Freilose mehr — alle Matches sind echte Spiele.

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

    # Alle Matches für alle Runden erstellen
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
                # Ungerade Position → home, Gerade → away
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
        match.status = "scheduled"  # Alle sind echte Spiele (keine Freilose)

    return all_matches


def generate_ko_brackets_v2(season_id: int, db: Session) -> Dict:
    """
    Orchestriert Generierung aller 3 Brackets nach v2-Logik (KEINE Freilose).

    Prozess:
    1. Qualifizierte Teams mit Aufrücker-Logik ermitteln
    2. Pro Bracket: KOBracket erstellen, Teams seeden, Matches generieren
    3. Alles in DB persistieren

    Args:
        season_id: ID der Saison
        db: SQLAlchemy Session

    Returns:
        Dict mit Zusammenfassung pro Bracket:
        {
            "meister": {
                "bracket_id": X,
                "matches_count": Y,
                "rounds": Z,
                "teams_count": N,
                "aufruecker_count": M
            },
            ...
        }

    Raises:
        ValueError: wenn Season archived oder Gruppen nicht abgeschlossen
    """
    qualified = get_qualified_teams_v2(season_id, db)  # prüft archived intern
    result = {}

    for bracket_type in ["meister", "lucky_loser", "loser"]:
        teams = qualified[bracket_type]

        if teams is None:
            result[bracket_type] = {
                "bracket_id": None,
                "matches_count": 0,
                "rounds": 0,
                "teams_count": 0,
                "message": "Nicht genug Teams — Bracket nicht generiert"
            }
            continue

        bracket = models.KOBracket(
            season_id=season_id,
            bracket_type=bracket_type,
            status="active",
            generated_at=datetime.utcnow()
        )
        db.add(bracket)
        db.flush()

        pairs = seed_teams(teams)
        matches = generate_rounds(
            pairs=pairs,
            bracket_id=bracket.id,
            season_id=season_id,
            bracket_type=bracket_type,
            db=db
        )

        total_rounds = int(math.log2(len(teams)))
        result[bracket_type] = {
            "bracket_id": bracket.id,
            "matches_count": len(matches),
            "rounds": total_rounds,
            "teams_count": len(teams),
            "aufruecker_count": len(qualified["aufruecker_info"][bracket_type])
        }

    db.commit()
    return result


def preview_ko_brackets(season_id: int, db: Session) -> Dict:
    """
    Berechnet was generate_ko_brackets_v2 tun würde, OHNE DB-Writes.

    Nützlich für Admin-UI zur Vorschau vor Generierung.

    Args:
        season_id: ID der Saison
        db: SQLAlchemy Session

    Returns:
        {
            "meister": {
                "teams": [...team_ids...],
                "size": 8|16,
                "rounds": int,
                "aufruecker": [aufruecker_team_ids],
                "pairings_r1": [{"home": team_id, "away": team_id}, ...]
            },
            "lucky_loser": {...} | None,
            "loser": {...} | None,
            "team_names": {team_id: name, ...}
        }

    Raises:
        ValueError: wenn Season archived oder Gruppen nicht abgeschlossen
    """
    qualified = get_qualified_teams_v2(season_id, db)  # nur DB reads

    # Team-Namen für alle beteiligten IDs sammeln
    all_ids = set()
    for bt in ["meister", "lucky_loser", "loser"]:
        if qualified[bt]:
            all_ids.update(qualified[bt])

    team_names = {}
    for tid in all_ids:
        team = db.get(models.Team, tid)
        team_names[tid] = team.name if team else f"Team#{tid}"

    result = {}
    for bracket_type in ["meister", "lucky_loser", "loser"]:
        teams = qualified[bracket_type]
        if teams is None:
            result[bracket_type] = None
            continue

        pairs = seed_teams(teams)
        result[bracket_type] = {
            "teams": teams,
            "size": len(teams),
            "rounds": int(math.log2(len(teams))),
            "aufruecker": qualified["aufruecker_info"][bracket_type],
            "pairings_r1": [
                {"home": h, "away": a} for h, a in pairs
            ]
        }

    result["team_names"] = team_names
    return result
