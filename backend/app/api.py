import math
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, schemas
from .db import SessionLocal, engine
from .auth import get_current_user, verify_credentials, create_jwt_token
from .ko_bracket_generator import generate_ko_brackets
from . import ranking_service

models.Base.metadata.create_all(bind=engine)

router = APIRouter()


# ============ AUTH ============

@router.post("/login", response_model=schemas.LoginResponse)
def login(request: schemas.LoginRequest):
    """Login mit Username/Passwort, gibt JWT Token zurück."""
    if not verify_credentials(request.username, request.password):
        raise HTTPException(status_code=401, detail="Ungültige Anmeldedaten")
    
    token = create_jwt_token(request.username)
    return schemas.LoginResponse(
        access_token=token,
        username=request.username,
    )


@router.get("/me")
def get_me(current_user: str = Depends(get_current_user)):
    """Gibt den aktuellen User zurück (Auth-Test)."""
    return {"username": current_user}


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/seasons", response_model=schemas.SeasonRead)
def create_season(season: schemas.SeasonCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    # 1. Saison anlegen
    obj = models.Season(
        name=season.name,
        participant_count=season.participant_count,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    # 2. Gruppen automatisch erzeugen (max. 4 Teams pro Gruppe)
    max_per_group = 4
    group_count = (season.participant_count + max_per_group - 1) // max_per_group

    for i in range(group_count):
        group_name = chr(ord('A') + i)
        group = models.Group(
            season_id=obj.id,
            name=group_name,
            sort_order=i + 1,
        )
        db.add(group)

    db.commit()
    return obj


@router.get("/seasons", response_model=list[schemas.SeasonRead])
def list_seasons(db: Session = Depends(get_db)):
    return db.query(models.Season).order_by(models.Season.created_at.desc()).all()


@router.get("/seasons/{season_id}", response_model=schemas.SeasonRead)
def get_season(season_id: int, db: Session = Depends(get_db)):
    season = db.query(models.Season).filter(models.Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")
    return season


@router.patch("/seasons/{season_id}", response_model=schemas.SeasonRead)
def update_season(season_id: int, update: schemas.SeasonUpdate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """Aktualisiert eine Saison (Name und Status)"""
    season = db.query(models.Season).filter(models.Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")

    if update.name is not None:
        season.name = update.name
    if update.status is not None:
        season.status = update.status

    db.commit()
    db.refresh(season)
    return season


@router.delete("/seasons/{season_id}")
def delete_season(season_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """Löscht eine Saison komplett (inkl. Gruppen, Teams, Matches)"""
    season = db.query(models.Season).filter(models.Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")

    # Cascade delete wird von SQLAlchemy/DB automatisch gemacht
    # Aber wir machen es explizit für Klarheit:

    # 1. KO-Matches löschen
    db.query(models.KOMatch).filter(models.KOMatch.season_id == season_id).delete()

    # 2. Matches löschen
    db.query(models.Match).filter(models.Match.season_id == season_id).delete()

    # 3. SeasonTeams löschen
    db.query(models.SeasonTeam).filter(models.SeasonTeam.season_id == season_id).delete()

    # 4. Gruppen löschen
    db.query(models.Group).filter(models.Group.season_id == season_id).delete()

    # 5. News löschen (falls saisonspezifisch)
    # db.query(models.News).filter(models.News.season_id == season_id).delete()

    # 6. Saison selbst löschen
    db.delete(season)
    db.commit()

    return {"deleted": True, "id": season_id}


# Gruppen werden automatisch beim Erstellen einer Saison erzeugt
# Manueller Gruppen-Create-Endpunkt wurde entfernt


@router.get("/seasons/{season_id}/groups", response_model=list[schemas.GroupRead])
def list_groups(season_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Group)
        .filter(models.Group.season_id == season_id)
        .order_by(models.Group.sort_order)
        .all()
    )


@router.get("/teams/search", response_model=list[schemas.TeamRead])
def search_teams(
    name: str,
    db: Session = Depends(get_db)
):
    """
    Sucht Teams nach Name (case-insensitive, partial match).
    Für Discord Bot Team-Claim Feature.
    """
    # Validation: min 2 chars
    if len(name.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Suchbegriff muss mindestens 2 Zeichen lang sein"
        )

    teams = db.query(models.Team).filter(
        models.Team.name.ilike(f"%{name}%")
    ).limit(10).all()

    return [{"id": t.id, "name": t.name} for t in teams]


@router.get("/teams/{team_id}", response_model=schemas.TeamDetail)
def get_team_detail(team_id: int, db: Session = Depends(get_db)):
    """Holt Team-Details mit letzten 5 Spielen"""
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Alle Matches des Teams (Gruppenphase + KO) - KEINE Limit!
    group_matches = db.query(models.Match).filter(
        (models.Match.home_team_id == team_id) | (models.Match.away_team_id == team_id)
    ).order_by(models.Match.id.desc()).all()

    ko_matches = db.query(models.KOMatch).filter(
        (models.KOMatch.home_team_id == team_id) | (models.KOMatch.away_team_id == team_id)
    ).order_by(models.KOMatch.id.desc()).all()

    # Kombinieren und sortieren
    all_matches = []

    for m in group_matches:
        is_home = m.home_team_id == team_id
        opponent_id = m.away_team_id if is_home else m.home_team_id
        opponent = db.query(models.Team).filter(models.Team.id == opponent_id).first()
        season = db.query(models.Season).filter(models.Season.id == m.season_id).first()

        own_goals = m.home_goals if is_home else m.away_goals
        opp_goals = m.away_goals if is_home else m.home_goals

        result = "scheduled"
        if m.home_goals is not None and m.away_goals is not None:
            if own_goals > opp_goals:
                result = "win"
            elif own_goals < opp_goals:
                result = "loss"
            else:
                result = "draw"

        all_matches.append(schemas.TeamDetailMatch(
            id=m.id,
            season_name=season.name if season else "?",
            opponent_id=opponent_id,
            opponent_name=opponent.name if opponent else "?",
            is_home=is_home,
            own_goals=own_goals,
            opponent_goals=opp_goals,
            result=result,
            date=None
        ))

    for m in ko_matches:
        if not m.is_bye:
            is_home = m.home_team_id == team_id
            opponent_id = m.away_team_id if is_home else m.home_team_id
            if opponent_id:
                opponent = db.query(models.Team).filter(models.Team.id == opponent_id).first()
                season = db.query(models.Season).filter(models.Season.id == m.season_id).first()

                own_goals = m.home_goals if is_home else m.away_goals
                opp_goals = m.away_goals if is_home else m.home_goals

                result = "scheduled"
                if m.home_goals is not None and m.away_goals is not None:
                    if own_goals > opp_goals:
                        result = "win"
                    elif own_goals < opp_goals:
                        result = "loss"

                all_matches.append(schemas.TeamDetailMatch(
                    id=m.id,
                    season_name=season.name if season else "?",
                    opponent_id=opponent_id,
                    opponent_name=opponent.name if opponent else "?",
                    is_home=is_home,
                    own_goals=own_goals,
                    opponent_goals=opp_goals,
                    result=result,
                    date=None
                ))

    # Statistiken aus ALLEN Spielen berechnen
    all_matches_sorted = sorted(all_matches, key=lambda x: x.id, reverse=True)
    wins = sum(1 for m in all_matches_sorted if m.result == "win")
    draws = sum(1 for m in all_matches_sorted if m.result == "draw")
    losses = sum(1 for m in all_matches_sorted if m.result == "loss")

    # Nur die letzten 5 für die Anzeige
    recent_matches = all_matches_sorted[:5]

    # Discord-Claim-Status überprüfen
    discord_claimed = db.query(models.UserProfile).filter(
        models.UserProfile.team_id == team_id
    ).first() is not None

    return schemas.TeamDetail(
        id=team.id,
        name=team.name,
        logo_url=team.logo_url,
        onlineliga_url=team.onlineliga_url,
        discord_claimed=discord_claimed,
        recent_matches=recent_matches,
        stats={
            "played": wins + draws + losses,
            "wins": wins,
            "draws": draws,
            "losses": losses
        }
    )


@router.patch("/teams/{team_id}", response_model=schemas.TeamRead)
def update_team(team_id: int, update: schemas.TeamUpdate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """Aktualisiert Team-Daten (Name, Logo, Onlineliga-Link)"""
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if update.name is not None:
        team.name = update.name
    if update.logo_url is not None:
        team.logo_url = update.logo_url
    if update.onlineliga_url is not None:
        team.onlineliga_url = update.onlineliga_url

    db.commit()
    db.refresh(team)
    return team


@router.post("/seasons/{season_id}/teams", response_model=schemas.TeamRead)
def add_team_to_season(season_id: int, team: schemas.TeamCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    # Prüfen, ob Team mit diesem Namen bereits existiert
    existing_team = db.query(models.Team).filter(models.Team.name == team.name).first()

    if existing_team:
        # Existierendes Team wiederverwenden
        t = existing_team
    else:
        # Neues Team erstellen
        t = models.Team(
            name=team.name,
            logo_url=team.logo_url,
            onlineliga_url=team.onlineliga_url
        )
        db.add(t)
        db.commit()
        db.refresh(t)

    # Gruppenzuweisung: Explizit (falls group_id gegeben) oder automatisch (kleinste Gruppe)
    if team.group_id is not None:
        # Explizite Gruppenzuweisung (z.B. für Import)
        target_group_id = team.group_id
        # Validierung: Gruppe muss zur Season gehören
        group = db.query(models.Group).filter(
            models.Group.id == target_group_id,
            models.Group.season_id == season_id
        ).first()
        if not group:
            raise HTTPException(status_code=400, detail=f"Group {target_group_id} not found in season {season_id}")
    else:
        # Automatische Verteilung auf kleinste Gruppe
        groups = db.query(models.Group).filter(models.Group.season_id == season_id).order_by(models.Group.sort_order).all()
        counts = {g.id: db.query(models.SeasonTeam).filter(models.SeasonTeam.group_id == g.id).count() for g in groups}
        target_group_id = min(counts, key=counts.get)

    st = models.SeasonTeam(season_id=season_id, team_id=t.id, group_id=target_group_id)
    db.add(st)
    db.commit()

    return t


@router.post("/seasons/{season_id}/teams/bulk")
def bulk_add_teams(season_id: int, payload: schemas.BulkTeamCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    groups = db.query(models.Group).filter(models.Group.season_id == season_id).order_by(models.Group.sort_order).all()
    if not groups:
        raise HTTPException(status_code=400, detail="No groups for season")

    created = []
    for name in payload.teams:
        # Prüfen, ob Team mit diesem Namen bereits existiert
        existing_team = db.query(models.Team).filter(models.Team.name == name).first()

        if existing_team:
            # Existierendes Team wiederverwenden
            t = existing_team
        else:
            # Neues Team erstellen
            t = models.Team(name=name)
            db.add(t)
            db.commit()
            db.refresh(t)

        counts = {g.id: db.query(models.SeasonTeam).filter(models.SeasonTeam.group_id == g.id).count() for g in groups}
        target_group_id = min(counts, key=counts.get)

        st = models.SeasonTeam(season_id=season_id, team_id=t.id, group_id=target_group_id)
        db.add(st)
        db.commit()

        created.append({"id": t.id, "name": t.name, "group_id": target_group_id})

    return {
        "created": created,
        "count": len(created)
    }


@router.get("/seasons/{season_id}/groups-with-teams")
def list_groups_with_teams(season_id: int, db: Session = Depends(get_db)):
    groups = db.query(models.Group).filter(models.Group.season_id == season_id).order_by(models.Group.sort_order).all()
    result = []
    for g in groups:
        teams = (
            db.query(models.Team)
            .join(models.SeasonTeam, models.SeasonTeam.team_id == models.Team.id)
            .filter(models.SeasonTeam.group_id == g.id)
            .all()
        )
        matches = (
            db.query(models.Match)
            .filter(models.Match.group_id == g.id)
            .all()
        )
        result.append({
            "group": {"id": g.id, "name": g.name},
            "teams": [{"id": t.id, "name": t.name} for t in teams],
            "matches": [
                {
                    "id": m.id,
                    "home_team_id": m.home_team_id,
                    "away_team_id": m.away_team_id,
                    "home_goals": m.home_goals,
                    "away_goals": m.away_goals,
                    "status": m.status,
                }
                for m in matches
            ],
        })
    return result


@router.post("/groups/{group_id}/matches", response_model=schemas.MatchRead)
def create_match(group_id: int, match: schemas.MatchCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    obj = models.Match(
        season_id=group.season_id,
        group_id=group_id,
        home_team_id=match.home_team_id,
        away_team_id=match.away_team_id,
        home_goals=match.home_goals,
        away_goals=match.away_goals,
        status=match.status if match.status else "scheduled",
        matchday=match.matchday,
        ingame_week=match.ingame_week,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/matches/{match_id}", response_model=schemas.MatchRead)
def update_match(match_id: int, update: schemas.MatchUpdate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """
    Ergebnis eines Matches eintragen oder aktualisieren.
    Setzt Status automatisch auf 'played' wenn Tore eingetragen werden.
    """
    match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if update.home_goals is not None:
        match.home_goals = update.home_goals
    if update.away_goals is not None:
        match.away_goals = update.away_goals
    if update.status is not None:
        match.status = update.status
    if update.ingame_week is not None:
        match.ingame_week = update.ingame_week

    # Auto-Status: wenn beide Tore gesetzt → played
    if match.home_goals is not None and match.away_goals is not None:
        if match.status == "scheduled":
            match.status = "played"

    db.commit()
    db.refresh(match)
    return match


@router.post("/groups/{group_id}/generate-schedule")
def generate_group_schedule(group_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """
    Generiert einen vollständigen Gruppen-Spielplan (Round-Robin) mit Spieltagen.
    Verwendet Circle-Methode für gleichmäßige Spieltag-Verteilung.
    """
    team_ids = [
        st.team_id
        for st in db.query(models.SeasonTeam)
        .filter(models.SeasonTeam.group_id == group_id)
        .all()
    ]

    if len(team_ids) < 2:
        raise HTTPException(status_code=400, detail="Not enough teams for schedule")

    existing = db.query(models.Match).filter(models.Match.group_id == group_id).count()
    if existing > 0:
        raise HTTPException(status_code=400, detail="Schedule already exists")

    group = db.get(models.Group, group_id)
    season_id = group.season_id

    # Circle-Methode für Round-Robin mit Spieltagen
    n = len(team_ids)
    teams = team_ids.copy()

    # Bei ungerader Anzahl: "Bye" hinzufügen
    if n % 2 == 1:
        teams.append(None)
        n += 1

    matchdays = []
    for round_num in range(n - 1):
        round_matches = []
        for i in range(n // 2):
            home = teams[i]
            away = teams[n - 1 - i]

            # Skip wenn Bye
            if home is not None and away is not None:
                round_matches.append((home, away))

        matchdays.append(round_matches)

        # Rotation (erstes Team bleibt fix, Rest rotiert)
        teams = [teams[0]] + [teams[-1]] + teams[1:-1]

    # Matches in DB erstellen
    created = []
    for matchday_num, matches in enumerate(matchdays, start=1):
        for home_id, away_id in matches:
            m = models.Match(
                season_id=season_id,
                group_id=group_id,
                home_team_id=home_id,
                away_team_id=away_id,
                status="scheduled",
                matchday=matchday_num
            )
            db.add(m)
            created.append(m)

    db.commit()
    return {"group_id": group_id, "matches_created": len(created), "matchdays": len(matchdays)}


@router.get("/groups/{group_id}/standings")
def group_standings(group_id: int, db: Session = Depends(get_db)):
    """
    Berechnet die Tabelle einer Gruppe on-the-fly.
    Punkte: Sieg 3, Unentschieden 1, Niederlage 0
    Sortierung: Punkte, Tordifferenz, Tore
    """
    matches = db.query(models.Match).filter(models.Match.group_id == group_id).all()
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
        for st in db.query(models.SeasonTeam).filter(models.SeasonTeam.group_id == group_id).all()
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
    table.sort(key=lambda x: (x["points"], x["goals_for"] - x["goals_against"], x["goals_for"]), reverse=True)
    return table


@router.get("/seasons/{season_id}/ko-plan", response_model=schemas.KOPlan)
def ko_plan(season_id: int, db: Session = Depends(get_db)):
    """
    Erstellt einen logischen KO-Plan (ohne Persistenz).
    Annahme: Qualifiziert sind alle Teams der Saison (PoC).
    Freilose werden berechnet, falls keine Zweierpotenz.
    """
    # qualifizierte Teams ermitteln
    team_ids = [
        st.team_id
        for st in db.query(models.SeasonTeam)
        .filter(models.SeasonTeam.season_id == season_id)
        .all()
    ]

    if not team_ids:
        raise HTTPException(status_code=400, detail="No teams for season")

    import math

    def next_power_of_two(n: int) -> int:
        return 1 << (n - 1).bit_length()

    total = len(team_ids)
    bracket_size = next_power_of_two(total)
    byes_needed = bracket_size - total

    # einfache Strategie: erste Teams bekommen Freilose
    byes = team_ids[:byes_needed]
    remaining = team_ids[byes_needed:]

    rounds = []
    rounds.append(
        schemas.KORound(
            name="Runde 1",
            teams=remaining,
            byes=byes,
        )
    )

    return schemas.KOPlan(
        season_id=season_id,
        qualified_team_ids=team_ids,
        rounds=rounds,
    )


# ============ KO-BRACKET PERSISTENCE ============

def _next_power_of_two(n: int) -> int:
    return 1 << (n - 1).bit_length()


def _round_name(round_num: int, total_rounds: int) -> str:
    """Menschenlesbarer Rundenname."""
    remaining = total_rounds - round_num + 1
    if remaining == 1:
        return "Finale"
    elif remaining == 2:
        return "Halbfinale"
    elif remaining == 3:
        return "Viertelfinale"
    elif remaining == 4:
        return "Achtelfinale"
    else:
        return f"Runde {round_num}"


@router.post("/seasons/{season_id}/ko-bracket/generate", response_model=schemas.KOBracket)
def generate_ko_bracket(season_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """
    Generiert das komplette KO-Bracket und persistiert es.
    - Berechnet Bracket-Größe (nächste Zweierpotenz)
    - Verteilt Freilose
    - Erstellt alle Matches inkl. Verknüpfungen (next_match_id)
    """
    # Prüfen ob schon ein Bracket existiert
    existing = db.query(models.KOMatch).filter(models.KOMatch.season_id == season_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="KO bracket already exists for this season")

    # Teams holen (später: nur Gruppensieger/Zweite)
    team_ids = [
        st.team_id
        for st in db.query(models.SeasonTeam)
        .filter(models.SeasonTeam.season_id == season_id)
        .all()
    ]

    if len(team_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 teams for KO bracket")

    total_teams = len(team_ids)
    bracket_size = _next_power_of_two(total_teams)
    byes_needed = bracket_size - total_teams
    total_rounds = bracket_size.bit_length() - 1  # z.B. 16 Teams → 4 Runden

    # Teams aufteilen: erste X bekommen Freilose
    bye_teams = team_ids[:byes_needed]
    playing_teams = team_ids[byes_needed:]

    # Alle Matches erstellen (von hinten nach vorne für Verknüpfungen)
    all_matches = []

    # Erst alle Matches ohne Verknüpfung erstellen
    for round_num in range(total_rounds, 0, -1):
        matches_in_round = bracket_size // (2 ** round_num)
        for pos in range(1, matches_in_round + 1):
            match = models.KOMatch(
                season_id=season_id,
                round=round_num,
                position=pos,
                status="pending",
            )
            db.add(match)
            all_matches.append(match)

    db.flush()  # IDs generieren

    # Verknüpfungen setzen (Match → nächstes Match)
    for match in all_matches:
        if match.round < total_rounds:
            # Finde das Folge-Match
            next_round = match.round + 1
            next_pos = (match.position + 1) // 2
            next_match = next(
                (m for m in all_matches if m.round == next_round and m.position == next_pos),
                None
            )
            if next_match:
                match.next_match_id = next_match.id
                match.next_match_slot = "home" if match.position % 2 == 1 else "away"

    # Runde 1 befüllen
    round1_matches = sorted(
        [m for m in all_matches if m.round == 1],
        key=lambda m: m.position
    )

    # Freilose eintragen
    for i, team_id in enumerate(bye_teams):
        if i < len(round1_matches):
            match = round1_matches[i]
            match.home_team_id = team_id
            match.is_bye = 1
            match.status = "played"
            # Sieger direkt in nächste Runde
            if match.next_match_id:
                next_match = db.get(models.KOMatch, match.next_match_id)
                if next_match:
                    if match.next_match_slot == "home":
                        next_match.home_team_id = team_id
                    else:
                        next_match.away_team_id = team_id

    # Echte Matches befüllen
    match_idx = byes_needed
    for i in range(0, len(playing_teams), 2):
        if match_idx < len(round1_matches) and i + 1 < len(playing_teams):
            match = round1_matches[match_idx]
            match.home_team_id = playing_teams[i]
            match.away_team_id = playing_teams[i + 1]
            match.status = "scheduled"
            match_idx += 1

    db.commit()

    # Alle Matches zurückgeben
    matches = db.query(models.KOMatch).filter(models.KOMatch.season_id == season_id).all()
    return schemas.KOBracket(
        season_id=season_id,
        total_rounds=total_rounds,
        matches=[schemas.KOMatchRead.model_validate(m) for m in matches],
    )


@router.get("/seasons/{season_id}/ko-bracket", response_model=schemas.KOBracket)
def get_ko_bracket(season_id: int, db: Session = Depends(get_db)):
    """Holt das persistierte KO-Bracket einer Saison."""
    matches = (
        db.query(models.KOMatch)
        .filter(models.KOMatch.season_id == season_id)
        .order_by(models.KOMatch.round, models.KOMatch.position)
        .all()
    )

    if not matches:
        raise HTTPException(status_code=404, detail="No KO bracket found for this season")

    total_rounds = max(m.round for m in matches)
    return schemas.KOBracket(
        season_id=season_id,
        total_rounds=total_rounds,
        matches=[schemas.KOMatchRead.model_validate(m) for m in matches],
    )


@router.patch("/ko-matches/{match_id}", response_model=schemas.KOMatchRead)
def update_ko_match(match_id: int, update: schemas.KOMatchUpdate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """
    Ergebnis eines KO-Matches eintragen.
    Sieger wird automatisch ins nächste Match übertragen.
    """
    match = db.query(models.KOMatch).filter(models.KOMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="KO match not found")

    if match.is_bye:
        raise HTTPException(status_code=400, detail="Cannot update bye match")

    if update.home_team_id is not None:
        match.home_team_id = update.home_team_id
    if update.away_team_id is not None:
        match.away_team_id = update.away_team_id
    if update.home_goals is not None:
        match.home_goals = update.home_goals
    if update.away_goals is not None:
        match.away_goals = update.away_goals
    if update.status is not None:
        match.status = update.status
    if update.ingame_week is not None:
        match.ingame_week = update.ingame_week

    # Auto-Status und Sieger-Weiterleitung
    if match.home_goals is not None and match.away_goals is not None:
        match.status = "played"

        # Sieger ermitteln (bei Unentschieden: keine Auto-Weiterleitung)
        winner_id = None
        if match.home_goals > match.away_goals:
            winner_id = match.home_team_id
        elif match.away_goals > match.home_goals:
            winner_id = match.away_team_id

        # Sieger ins nächste Match eintragen
        if winner_id and match.next_match_id:
            next_match = db.get(models.KOMatch, match.next_match_id)
            if next_match:
                if match.next_match_slot == "home":
                    next_match.home_team_id = winner_id
                else:
                    next_match.away_team_id = winner_id
                # Wenn beide Teams da → scheduled
                if next_match.home_team_id and next_match.away_team_id:
                    next_match.status = "scheduled"

    db.commit()
    db.refresh(match)
    return match


# ============ NEWS ============

@router.post("/news", response_model=schemas.NewsRead)
def create_news(news: schemas.NewsCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """Neuen News-Artikel erstellen."""
    obj = models.News(
        title=news.title,
        content=news.content,
        author=news.author or "Admin",
        published=news.published if news.published is not None else 1,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/news", response_model=list[schemas.NewsRead])
def list_news(published_only: bool = True, db: Session = Depends(get_db)):
    """Alle News-Artikel abrufen. Default: nur veröffentlichte."""
    query = db.query(models.News)
    if published_only:
        query = query.filter(models.News.published == 1)
    return query.order_by(models.News.created_at.desc()).all()


@router.get("/news/{news_id}", response_model=schemas.NewsRead)
def get_news(news_id: int, db: Session = Depends(get_db)):
    """Einzelnen News-Artikel abrufen."""
    news = db.get(models.News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")
    return news


@router.patch("/news/{news_id}", response_model=schemas.NewsRead)
def update_news(news_id: int, update: schemas.NewsUpdate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """News-Artikel aktualisieren."""
    news = db.get(models.News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    if update.title is not None:
        news.title = update.title
    if update.content is not None:
        news.content = update.content
    if update.author is not None:
        news.author = update.author
    if update.published is not None:
        news.published = update.published

    db.commit()
    db.refresh(news)
    return news


@router.delete("/news/{news_id}")
def delete_news(news_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """News-Artikel löschen."""
    news = db.get(models.News, news_id)
    if not news:
        raise HTTPException(status_code=404, detail="News not found")

    db.delete(news)
    db.commit()
    return {"deleted": True, "id": news_id}


# ============ EWIGE TABELLE ============

@router.get("/seasons/{season_id}/matchdays")
def get_season_matchdays(season_id: int, db: Session = Depends(get_db)):
    """
    Gibt die maximale Spieltag-Nummer für eine Saison zurück.
    """
    from sqlalchemy import func

    max_matchday = db.query(func.max(models.Match.matchday)).filter(
        models.Match.season_id == season_id
    ).scalar()

    return {"max_matchday": max_matchday or 0}


@router.get("/seasons/{season_id}/matchday/{matchday}")
def get_season_matchday(season_id: int, matchday: int, db: Session = Depends(get_db)):
    """
    Holt alle Matches eines Spieltags über alle Gruppen einer Saison.
    """
    matches = db.query(models.Match).filter(
        models.Match.season_id == season_id,
        models.Match.matchday == matchday
    ).all()

    result = []
    for match in matches:
        result.append({
            "id": match.id,
            "group_id": match.group_id,
            "home_team_id": match.home_team_id,
            "away_team_id": match.away_team_id,
            "home_goals": match.home_goals,
            "away_goals": match.away_goals,
            "status": match.status,
            "matchday": match.matchday
        })

    return result


@router.get("/groups/{group_id}/matchdays")
def get_group_matchdays(group_id: int, db: Session = Depends(get_db)):
    """
    Gibt die Anzahl der Spieltage in einer Gruppe zurück.
    """
    from sqlalchemy import func

    max_matchday = db.query(func.max(models.Match.matchday)).filter(
        models.Match.group_id == group_id
    ).scalar()

    return {"max_matchday": max_matchday or 0}


@router.get("/groups/{group_id}/matchday/{matchday}")
def get_group_matchday(group_id: int, matchday: int, db: Session = Depends(get_db)):
    """
    Holt alle Matches eines bestimmten Spieltags in einer Gruppe.
    """
    matches = db.query(models.Match).filter(
        models.Match.group_id == group_id,
        models.Match.matchday == matchday
    ).all()

    result = []
    for match in matches:
        result.append({
            "id": match.id,
            "home_team_id": match.home_team_id,
            "away_team_id": match.away_team_id,
            "home_goals": match.home_goals,
            "away_goals": match.away_goals,
            "status": match.status,
            "matchday": match.matchday
        })

    return result


@router.get("/matches/batch")
def get_matches_batch(match_ids: str, db: Session = Depends(get_db)):
    """
    Mehrere Matches auf einmal abrufen für News-Embeddings.
    match_ids: Komma-separierte Liste von Match-IDs, z.B. "12,13,14,15"
    """
    try:
        ids = [int(id.strip()) for id in match_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid match_ids format")

    matches = db.query(models.Match).filter(models.Match.id.in_(ids)).all()

    result = []
    for match in matches:
        result.append({
            "id": match.id,
            "home_team_id": match.home_team_id,
            "away_team_id": match.away_team_id,
            "home_goals": match.home_goals,
            "away_goals": match.away_goals,
            "status": match.status
        })

    return result


@router.get("/ko-matches/batch")
def get_ko_matches_batch(match_ids: str, db: Session = Depends(get_db)):
    """
    Mehrere KO-Matches auf einmal abrufen für News-Embeddings.
    match_ids: Komma-separierte Liste von KO-Match-IDs, z.B. "5,6,7,8"
    """
    try:
        ids = [int(id.strip()) for id in match_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid match_ids format")

    matches = db.query(models.KOMatch).filter(
        models.KOMatch.id.in_(ids),
        models.KOMatch.is_bye == False
    ).all()

    result = []
    for match in matches:
        result.append({
            "id": match.id,
            "home_team_id": match.home_team_id,
            "away_team_id": match.away_team_id,
            "home_goals": match.home_goals,
            "away_goals": match.away_goals,
            "status": match.status
        })

    return result


@router.get("/all-time-standings")
def get_all_time_standings(db: Session = Depends(get_db)):
    """
    Ewige Tabelle: Aggregierte Statistiken aller Teams über alle Saisons.
    Berücksichtigt sowohl Gruppenphase als auch KO-Phase Spiele.
    Gruppiert nach Team-Namen (wegen historischer Duplikate).
    """
    # Alle Teams holen
    teams = db.query(models.Team).all()

    # Nach Team-Namen gruppieren (wegen Duplikaten aus Saison-Importen)
    team_stats = {}  # team_name -> stats dict

    for team in teams:
        if team.name not in team_stats:
            team_stats[team.name] = {
                "team_id": team.id,  # Erste gefundene ID verwenden
                "team_name": team.name,
                "played": 0,
                "won": 0,
                "draw": 0,
                "lost": 0,
                "goals_for": 0,
                "goals_against": 0,
                "points": 0
            }

        stats = team_stats[team.name]

        # Gruppenphase-Matches (als Heim-Team)
        home_matches = db.query(models.Match).filter(
            models.Match.home_team_id == team.id,
            models.Match.status == "played"
        ).all()

        for match in home_matches:
            stats["played"] += 1
            stats["goals_for"] += match.home_goals
            stats["goals_against"] += match.away_goals

            if match.home_goals > match.away_goals:
                stats["won"] += 1
                stats["points"] += 3
            elif match.home_goals == match.away_goals:
                stats["draw"] += 1
                stats["points"] += 1
            else:
                stats["lost"] += 1

        # Gruppenphase-Matches (als Auswärts-Team)
        away_matches = db.query(models.Match).filter(
            models.Match.away_team_id == team.id,
            models.Match.status == "played"
        ).all()

        for match in away_matches:
            stats["played"] += 1
            stats["goals_for"] += match.away_goals
            stats["goals_against"] += match.home_goals

            if match.away_goals > match.home_goals:
                stats["won"] += 1
                stats["points"] += 3
            elif match.away_goals == match.home_goals:
                stats["draw"] += 1
                stats["points"] += 1
            else:
                stats["lost"] += 1

        # KO-Phase-Matches (als Heim-Team)
        ko_home_matches = db.query(models.KOMatch).filter(
            models.KOMatch.home_team_id == team.id,
            models.KOMatch.status == "played",
            models.KOMatch.is_bye == False
        ).all()

        for match in ko_home_matches:
            stats["played"] += 1
            stats["goals_for"] += match.home_goals
            stats["goals_against"] += match.away_goals

            if match.home_goals > match.away_goals:
                stats["won"] += 1
                stats["points"] += 3
            else:
                stats["lost"] += 1

        # KO-Phase-Matches (als Auswärts-Team)
        ko_away_matches = db.query(models.KOMatch).filter(
            models.KOMatch.away_team_id == team.id,
            models.KOMatch.status == "played",
            models.KOMatch.is_bye == False
        ).all()

        for match in ko_away_matches:
            stats["played"] += 1
            stats["goals_for"] += match.away_goals
            stats["goals_against"] += match.home_goals

            if match.away_goals > match.home_goals:
                stats["won"] += 1
                stats["points"] += 3
            else:
                stats["lost"] += 1

    # Nur Teams mit mindestens einem Spiel aufnehmen
    standings = [stats for stats in team_stats.values() if stats["played"] > 0]

    # Sortiere nach Punkten, Tordifferenz, Tore geschossen
    standings.sort(
        key=lambda x: (
            x["points"],
            x["goals_for"] - x["goals_against"],
            x["goals_for"]
        ),
        reverse=True
    )

    return standings

# ============================================================
# DISCORD BOT ENDPOINTS
# ============================================================

@router.post("/discord/users/ensure", response_model=schemas.UserProfileResponse)
def ensure_user(
    user_data: schemas.UserEnsureRequest,
    db: Session = Depends(get_db)
):
    """
    Upsert-Endpoint: Erstellt User falls nicht vorhanden, aktualisiert sonst username/avatar.
    Public Endpoint (kein Auth) - wird vom Discord Bot bei jedem Command aufgerufen.

    Logic:
        1. Suche User anhand discord_id
        2. Falls gefunden: Update username/avatar + updated_at
        3. Falls nicht gefunden: Erstelle neuen User mit participating_next=True
        4. Return full UserProfileResponse
    """
    from datetime import datetime

    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == user_data.discord_id
    ).first()

    if user:
        # Update existing user
        if user_data.discord_username is not None:
            user.discord_username = user_data.discord_username
        if user_data.discord_avatar_url is not None:
            user.discord_avatar_url = user_data.discord_avatar_url
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
    else:
        # Create new user
        user = models.UserProfile(
            discord_id=user_data.discord_id,
            discord_username=user_data.discord_username,
            discord_avatar_url=user_data.discord_avatar_url,
            participating_next=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Get team name for response
    team_name = None
    if user.team_id:
        team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
        if team:
            team_name = team.name

    return schemas.UserProfileResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar_url=user.discord_avatar_url,
        team_id=user.team_id,
        team_name=team_name,
        profile_url=user.profile_url,
        participating_next=user.participating_next,
        crest_url=user.crest_url,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.get("/discord/users/{discord_id}", response_model=schemas.UserProfileResponse)
def get_user_by_discord_id(
    discord_id: str,
    db: Session = Depends(get_db)
):
    """
    Holt User-Profil anhand Discord ID.
    Public Endpoint (kein Auth) - wird vom Discord Bot verwendet.
    """
    # User suchen
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Kein User mit Discord ID {discord_id} gefunden"
        )
    
    # Team-Name joinen wenn vorhanden
    team_name = None
    if user.team_id:
        team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
        if team:
            team_name = team.name
    
    # Response bauen
    return schemas.UserProfileResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar_url=user.discord_avatar_url,
        team_id=user.team_id,
        team_name=team_name,
        profile_url=user.profile_url,
        participating_next=user.participating_next,
        crest_url=user.crest_url,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.patch("/discord/users/{discord_id}/participation", response_model=schemas.UserProfileResponse)
def update_participation(
    discord_id: str,
    update: schemas.ParticipationUpdate,
    db: Session = Depends(get_db)
):
    """
    Setzt Teilnahme-Status für nächsten Pokal.
    Verwendet vom Discord Bot via /dabei Command.
    """
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Kein User mit Discord ID {discord_id} gefunden"
        )
    
    # Teilnahme-Status updaten
    user.participating_next = update.participating
    db.commit()
    db.refresh(user)
    
    # Team-Name joinen
    team_name = None
    if user.team_id:
        team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
        if team:
            team_name = team.name
    
    return schemas.UserProfileResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar_url=user.discord_avatar_url,
        team_id=user.team_id,
        team_name=team_name,
        profile_url=user.profile_url,
        participating_next=user.participating_next,
        crest_url=user.crest_url,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.patch("/discord/users/{discord_id}/profile", response_model=schemas.UserProfileResponse)
def update_profile_url(
    discord_id: str,
    update: schemas.ProfileUrlUpdate,
    db: Session = Depends(get_db)
):
    """
    Speichert Onlineliga Profil-URL.
    Verwendet vom Discord Bot via /profil Command.
    """
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Kein User mit Discord ID {discord_id} gefunden"
        )
    
    # Profil-URL updaten
    user.profile_url = str(update.profile_url)
    db.commit()
    db.refresh(user)
    
    # Team-Name joinen
    team_name = None
    if user.team_id:
        team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
        if team:
            team_name = team.name
    
    return schemas.UserProfileResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar_url=user.discord_avatar_url,
        team_id=user.team_id,
        team_name=team_name,
        profile_url=user.profile_url,
        participating_next=user.participating_next,
        crest_url=user.crest_url,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.patch("/discord/users/{discord_id}", response_model=schemas.UserProfileResponse)
def update_user_profile(
    discord_id: str,
    update_data: schemas.UserProfileAdminUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)  # Admin-Only
):
    """
    Aktualisiert ein User-Profil (Admin only).
    Nur übergebene Felder werden aktualisiert.
    Verwendet vom Discord Bot für Team-Verknüpfung etc.
    """
    # User finden
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User mit Discord ID {discord_id} nicht gefunden"
        )

    # Nur übergebene Felder aktualisieren
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(user, field, value)

    # Updated timestamp setzen
    from datetime import datetime
    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    # Team-Name laden falls team_id gesetzt
    team_name = None
    if user.team_id:
        team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
        if team:
            team_name = team.name

    return schemas.UserProfileResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar_url=user.discord_avatar_url,
        team_id=user.team_id,
        team_name=team_name,
        profile_url=user.profile_url,
        participating_next=user.participating_next,
        crest_url=user.crest_url,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.post("/discord/users/register", response_model=schemas.UserProfileResponse)
def register_discord_user(
    user_data: schemas.UserProfileCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)  # Admin-Only
):
    """
    Registriert neuen Discord User.
    Admin-Only Endpoint (erfordert Auth).
    """
    # Prüfe ob User bereits existiert
    existing = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == user_data.discord_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"User mit Discord ID {user_data.discord_id} existiert bereits"
        )

    # Neuen User anlegen
    user = models.UserProfile(
        discord_id=user_data.discord_id,
        discord_username=user_data.discord_username,
        profile_url=str(user_data.profile_url) if user_data.profile_url else None,
        team_id=user_data.team_id,
        participating_next=user_data.participating_next
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    # Team-Name joinen
    team_name = None
    if user.team_id:
        team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
        if team:
            team_name = team.name

    return schemas.UserProfileResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar_url=user.discord_avatar_url,
        team_id=user.team_id,
        team_name=team_name,
        profile_url=user.profile_url,
        participating_next=user.participating_next,
        crest_url=user.crest_url,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.post("/discord/users/{discord_id}/claim-team", response_model=schemas.UserProfileResponse)
def claim_team(
    discord_id: str,
    claim_data: schemas.TeamClaimRequest,
    db: Session = Depends(get_db)
):
    """
    User claimed ein Team (Self-Service).

    Validations (in order):
        1. User muss existieren (404)
        2. User muss Profil-URL gesetzt haben (403)
        3. Team muss existieren (404)
        4. User darf noch kein Team haben (409 "du hast bereits ein Team")
        5. Team darf nicht von anderem User geclaimed sein (409 "bereits von anderem User verknüpft")

    Success:
        200 OK mit aktualisiertem UserProfileResponse
    """
    from datetime import datetime

    team_id = claim_data.team_id

    # 1. User existiert? (muss existieren, da ensure_user vorher aufgerufen wurde)
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User mit Discord ID {discord_id} nicht gefunden"
        )

    # 2. User muss Profil-URL gesetzt haben
    if not user.profile_url or user.profile_url.strip() == "":
        raise HTTPException(
            status_code=403,
            detail="PROFILE_URL_REQUIRED"
        )

    # 3. Team existiert?
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team nicht gefunden")

    # 4. User hat bereits ein Team?
    if user.team_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Du hast bereits ein Team verknüpft"
        )

    # 5. Team schon von anderem User vergeben?
    existing_claim = db.query(models.UserProfile).filter(
        models.UserProfile.team_id == team_id,
        models.UserProfile.discord_id != discord_id
    ).first()
    if existing_claim:
        raise HTTPException(
            status_code=409,
            detail="Team ist bereits von einem anderen User verknüpft"
        )

    # Alles OK -> Team verknüpfen
    user.team_id = team_id
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return schemas.UserProfileResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar_url=user.discord_avatar_url,
        team_id=user.team_id,
        team_name=team.name,
        profile_url=user.profile_url,
        participating_next=user.participating_next,
        crest_url=user.crest_url,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.get("/discord/participation-report", response_model=schemas.ParticipationReport)
def get_participation_report(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)  # Admin-Only
):
    """
    Admin-Endpoint: Report über Teilnahme-Status aller User.
    """
    # Alle User holen
    users = db.query(models.UserProfile).all()
    
    total = len(users)
    participating = sum(1 for u in users if u.participating_next is True)
    not_participating = sum(1 for u in users if u.participating_next is False)
    
    # Participation Rate berechnen
    rate = (participating / total * 100) if total > 0 else 0.0
    
    # User-Liste mit Team-Namen
    user_responses = []
    for user in users:
        team_name = None
        if user.team_id:
            team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
            if team:
                team_name = team.name
        
        user_responses.append(schemas.UserProfileResponse(
            id=user.id,
            discord_id=user.discord_id,
            discord_username=user.discord_username,
            discord_avatar_url=user.discord_avatar_url,
            team_id=user.team_id,
            team_name=team_name,
            profile_url=user.profile_url,
            participating_next=user.participating_next,
            crest_url=user.crest_url,
            created_at=user.created_at,
            updated_at=user.updated_at
        ))
    
    return schemas.ParticipationReport(
        total_users=total,
        participating=participating,
        not_participating=not_participating,
        participation_rate=rate,
        users=user_responses
    )


@router.get("/discord/users", response_model=list[schemas.UserProfileResponse])
def list_discord_users(
    search: Optional[str] = None,
    has_team: Optional[bool] = None,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)  # Admin-Only (JWT oder API-Key)
):
    """
    Admin-Endpoint: Liste aller Discord User mit Filteroptionen.

    Query-Parameter:
        - search: Optional, filtert auf discord_username (ILIKE)
        - has_team: Optional, filtert ob team_id gesetzt ist (true) oder nicht (false)

    Returns:
        Liste von UserProfileResponse mit team_name
    """
    # Base query
    query = db.query(models.UserProfile)

    # Filter: search
    if search:
        query = query.filter(
            models.UserProfile.discord_username.ilike(f"%{search}%")
        )

    # Filter: has_team
    if has_team is not None:
        if has_team:
            query = query.filter(models.UserProfile.team_id.isnot(None))
        else:
            query = query.filter(models.UserProfile.team_id.is_(None))

    # Order by created_at desc
    users = query.order_by(models.UserProfile.created_at.desc()).all()

    # Response mit team_name
    user_responses = []
    for user in users:
        team_name = None
        if user.team_id:
            team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
            if team:
                team_name = team.name

        user_responses.append(schemas.UserProfileResponse(
            id=user.id,
            discord_id=user.discord_id,
            discord_username=user.discord_username,
            discord_avatar_url=user.discord_avatar_url,
            team_id=user.team_id,
            team_name=team_name,
            profile_url=user.profile_url,
            participating_next=user.participating_next,
            crest_url=user.crest_url,
            created_at=user.created_at,
            updated_at=user.updated_at
        ))

    return user_responses


@router.delete("/discord/users/{discord_id}", response_model=schemas.UserDeleteResponse)
def delete_discord_user(
    discord_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)  # Admin-Only
):
    """
    Admin-Endpoint: Löscht einen Discord User.

    Returns:
        UserDeleteResponse mit deleted=true
    """
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User mit Discord ID {discord_id} nicht gefunden"
        )

    db.delete(user)
    db.commit()

    return schemas.UserDeleteResponse(
        deleted=True,
        discord_id=discord_id
    )


@router.patch("/discord/users/{discord_id}/admin-set-team", response_model=schemas.UserProfileResponse)
def admin_set_team(
    discord_id: str,
    team_data: schemas.AdminSetTeamRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)  # Admin-Only
):
    """
    Admin-Endpoint: Setzt Team für User (ohne Konfliktprüfung).
    Admin kann Team überschreiben oder entfernen (team_id=null).

    Body:
        - team_id: int | null (null = Verknüpfung entfernen)

    Returns:
        Aktualisiertes UserProfileResponse
    """
    from datetime import datetime

    # User laden
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User mit Discord ID {discord_id} nicht gefunden"
        )

    # Team validieren (falls team_id gesetzt)
    team_name = None
    if team_data.team_id is not None:
        team = db.query(models.Team).filter(
            models.Team.id == team_data.team_id
        ).first()
        if not team:
            raise HTTPException(
                status_code=404,
                detail=f"Team mit ID {team_data.team_id} nicht gefunden"
            )
        team_name = team.name

    # Team setzen oder entfernen (kein Konflikt-Check)
    user.team_id = team_data.team_id
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return schemas.UserProfileResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar_url=user.discord_avatar_url,
        team_id=user.team_id,
        team_name=team_name,
        profile_url=user.profile_url,
        participating_next=user.participating_next,
        crest_url=user.crest_url,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


# ============================================================
# DISCORD OAUTH2 ENDPOINTS
# ============================================================

from .discord_oauth import DiscordOAuth2Client
from .auth import create_jwt_token
import secrets

# OAuth2 Client initialisieren
discord_oauth = DiscordOAuth2Client()

# State Storage (in Production: Redis verwenden!)
oauth_states = {}


@router.get("/auth/discord/login")
def discord_login():
    """
    Startet Discord OAuth2 Flow.
    Redirect zu Discord Authorization URL.
    """
    # CSRF State Token generieren
    state = secrets.token_urlsafe(32)
    oauth_states[state] = True  # Markiere State als gültig
    
    # Authorization URL generieren
    auth_url = discord_oauth.get_authorization_url(state)
    
    return {"authorization_url": auth_url}


@router.get("/auth/discord/callback", response_model=schemas.OAuth2CallbackResponse)
async def discord_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """
    Discord OAuth2 Callback.
    Tauscht Authorization Code gegen Access Token und erstellt/updated User.
    """
    # State validieren (CSRF Protection)
    if state not in oauth_states:
        raise HTTPException(status_code=400, detail="Ungültiger State (CSRF)")
    
    # State aus Storage entfernen (einmalig verwendbar)
    del oauth_states[state]
    
    # Access Token holen
    token = await discord_oauth.fetch_token(code)
    if not token:
        raise HTTPException(status_code=400, detail="Token Exchange fehlgeschlagen")
    
    # User-Info von Discord holen
    discord_user = await discord_oauth.fetch_user_info(token["access_token"])
    if not discord_user:
        raise HTTPException(status_code=400, detail="Konnte User-Info nicht abrufen")
    
    # User in DB erstellen oder updaten
    discord_id = discord_user["id"]
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()
    
    if not user:
        # Neuen User anlegen
        user = models.UserProfile(
            discord_id=discord_id,
            discord_username=f"{discord_user['username']}#{discord_user['discriminator']}",
            discord_avatar_url=discord_user.get("avatar"),
            participating_next=True
        )
        db.add(user)
    else:
        # Bestehenden User updaten
        user.discord_username = f"{discord_user['username']}#{discord_user['discriminator']}"
        user.discord_avatar_url = discord_user.get("avatar")
    
    # OAuth2 Token speichern (optional, für zukünftige API Calls)
    from datetime import datetime, timezone
    user.access_token = token["access_token"]
    user.refresh_token = token.get("refresh_token")
    user.token_expires_at = datetime.fromtimestamp(token["expires_at"], tz=timezone.utc)
    
    db.commit()
    db.refresh(user)
    
    # JWT Token für unsere API erstellen
    jwt_token = create_jwt_token(discord_id)
    
    # Team-Name joinen
    team_name = None
    if user.team_id:
        team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
        if team:
            team_name = team.name
    
    user_response = schemas.UserProfileResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar_url=user.discord_avatar_url,
        team_id=user.team_id,
        team_name=team_name,
        profile_url=user.profile_url,
        participating_next=user.participating_next,
        crest_url=user.crest_url,
        created_at=user.created_at,
        updated_at=user.updated_at
    )
    
    return schemas.OAuth2CallbackResponse(
        access_token=jwt_token,
        user=user_response
    )


# ============================================================
# FILE UPLOAD ENDPOINTS
# ============================================================

from fastapi import UploadFile, File
from .image_utils import validate_image_file, process_crest_image
import os
import aiofiles

# Upload-Verzeichnis aus Environment
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
CRESTS_DIR = os.path.join(UPLOAD_DIR, "crests")

# Sicherstellen dass Upload-Verzeichnis existiert
os.makedirs(CRESTS_DIR, exist_ok=True)


@router.post("/upload/crest", response_model=schemas.CrestUploadResponse)
async def upload_crest(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Wappen-Upload für eingeloggten User.
    Verarbeitet Bild (resize, WebP) und speichert es.
    """
    # User aus DB holen (current_user ist discord_id vom JWT)
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == current_user
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User-Profil nicht gefunden"
        )
    
    # Datei-Validierung
    file_size = 0
    file_content = await file.read()
    file_size = len(file_content)
    
    is_valid, error_msg = validate_image_file(
        file.filename,
        file.content_type,
        file_size
    )
    
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # Bild verarbeiten (resize, WebP)
    try:
        processed_image = await process_crest_image(file_content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Dateiname: {discord_id}.webp
    filename = f"{user.discord_id}.webp"
    filepath = os.path.join(CRESTS_DIR, filename)
    
    # Datei speichern
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(processed_image)
    
    # URL zum Wappen
    crest_url = f"/uploads/crests/{filename}"
    
    # User-Profil updaten
    user.crest_url = crest_url
    db.commit()
    
    return schemas.CrestUploadResponse(
        crest_url=crest_url,
        message="Wappen erfolgreich hochgeladen"
    )


@router.delete("/upload/crest", response_model=schemas.CrestDeleteResponse)
async def delete_crest(
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """
    Löscht eigenes Wappen.
    """
    # User aus DB holen
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == current_user
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User-Profil nicht gefunden")
    
    if not user.crest_url:
        raise HTTPException(status_code=404, detail="Kein Wappen vorhanden")
    
    # Datei löschen
    filename = f"{user.discord_id}.webp"
    filepath = os.path.join(CRESTS_DIR, filename)
    
    if os.path.exists(filepath):
        os.remove(filepath)
    
    # User-Profil updaten
    user.crest_url = None
    db.commit()
    
    return schemas.CrestDeleteResponse(
        message="Wappen erfolgreich gelöscht"
    )


@router.get("/upload/crest/{discord_id}")
def get_crest(discord_id: str, db: Session = Depends(get_db)):
    """
    Public Endpoint: Wappen eines Users abrufen.
    Redirect zur Datei oder 404 wenn nicht vorhanden.
    """
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()
    
    if not user or not user.crest_url:
        raise HTTPException(status_code=404, detail="Wappen nicht gefunden")
    
    # Redirect zur Datei (Nginx wird /uploads/ servieren)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=user.crest_url)


# ============================================================
# KO-BRACKET ENDPOINTS (3-Bracket-System)
# ============================================================

@router.post("/seasons/{season_id}/ko-brackets/generate", status_code=201)
def generate_season_ko_brackets(
    season_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """
    Generiert alle 3 KO-Brackets (Meister, Lucky Loser, Loser) für eine Saison.

    Prüft:
    - Ob alle Gruppen abgeschlossen sind (alle Matches gespielt)
    - Ob Brackets bereits existieren

    Returns:
        201: Brackets erfolgreich generiert mit Summary
        400: Gruppen nicht abgeschlossen
        409: Brackets bereits vorhanden
    """
    # Prüfe ob bereits Brackets existieren
    existing = db.query(models.KOBracket).filter(
        models.KOBracket.season_id == season_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="KO-Brackets bereits generiert für diese Saison"
        )

    # Generiere Brackets (wirft ValueError bei Validierungsfehlern)
    try:
        result = generate_ko_brackets(season_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


@router.get("/seasons/{season_id}/ko-brackets")
def get_season_ko_brackets(season_id: int, db: Session = Depends(get_db)):
    """
    Holt alle KO-Brackets einer Saison mit Matches.

    Response-Struktur:
    {
        "season_id": X,
        "brackets": {
            "meister": { ... },
            "lucky_loser": { ... },
            "loser": { ... }
        }
    }

    Falls ein Bracket nicht existiert: null
    """
    brackets_data = {}

    for bracket_type in ["meister", "lucky_loser", "loser"]:
        bracket = db.query(models.KOBracket).filter(
            models.KOBracket.season_id == season_id,
            models.KOBracket.bracket_type == bracket_type
        ).first()

        if not bracket:
            brackets_data[bracket_type] = None
            continue

        # Matches laden und nach Runden gruppieren
        matches = db.query(models.KOMatch).filter(
            models.KOMatch.season_id == season_id,
            models.KOMatch.bracket_type == bracket_type
        ).order_by(models.KOMatch.round, models.KOMatch.id).all()

        # Nach Runden gruppieren
        rounds_dict = {}
        for match in matches:
            round_key = f"runde_{match.round}"
            if round_key not in rounds_dict:
                rounds_dict[round_key] = []

            # Team-Daten laden
            home_team = None
            away_team = None

            if match.home_team_id:
                home = db.get(models.Team, match.home_team_id)
                if home:
                    home_team = {"id": home.id, "name": home.name}

            if match.away_team_id:
                away = db.get(models.Team, match.away_team_id)
                if away:
                    away_team = {"id": away.id, "name": away.name}

            # Winner ermitteln
            winner_id = None
            if match.home_goals is not None and match.away_goals is not None:
                if match.home_goals > match.away_goals:
                    winner_id = match.home_team_id
                elif match.away_goals > match.home_goals:
                    winner_id = match.away_team_id

            # Rundenname berechnen
            total_rounds = max(m.round for m in matches)
            round_name = _get_round_name(match.round, total_rounds)

            rounds_dict[round_key].append({
                "match_id": match.id,
                "round": round_name,
                "home_team": home_team,
                "away_team": away_team,
                "home_goals": match.home_goals,
                "away_goals": match.away_goals,
                "winner_id": winner_id,
                "is_bye": match.is_bye == 1,
                "status": match.status
            })

        brackets_data[bracket_type] = {
            "bracket_id": bracket.id,
            "status": bracket.status,
            "rounds": rounds_dict
        }

    return {
        "season_id": season_id,
        "brackets": brackets_data
    }


def _get_round_name(round_num: int, total_rounds: int) -> str:
    """Berechnet menschenlesbaren Rundennamen."""
    remaining = total_rounds - round_num + 1
    if remaining == 1:
        return "finale"
    elif remaining == 2:
        return "halbfinale"
    elif remaining == 3:
        return "viertelfinale"
    elif remaining == 4:
        return "achtelfinale"
    else:
        return f"runde_{round_num}"


@router.patch("/ko-matches/{match_id}")
def update_ko_match_result(
    match_id: int,
    update: dict,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """
    Trägt Ergebnis für ein KO-Match ein.

    Body:
        - home_goals: int (>= 0)
        - away_goals: int (>= 0)
        - winner_id: int | null (optional bei Unentschieden - wird automatisch via Tiebreaker ermittelt)

    Bei Unentschieden:
        - Falls winner_id gegeben: verwende diesen
        - Falls winner_id NICHT gegeben: automatischer Tiebreaker via Onlineliga-Ranking

    Bei regulärem Sieg wird winner_id automatisch berechnet.

    Nach Eintragen:
    - match.status = "played"
    - Sieger wird in next_match weitergeleitet
    - Falls alle Matches gespielt: bracket.status = "completed"
    """
    match = db.query(models.KOMatch).filter(
        models.KOMatch.id == match_id
    ).first()

    if not match:
        raise HTTPException(status_code=404, detail="KO-Match nicht gefunden")

    if match.is_bye == 1:
        raise HTTPException(status_code=400, detail="Freilos-Matches können nicht aktualisiert werden")

    # Validierung
    home_goals = update.get("home_goals")
    away_goals = update.get("away_goals")
    winner_id = update.get("winner_id")

    if home_goals is None or away_goals is None:
        raise HTTPException(
            status_code=400,
            detail="home_goals und away_goals sind erforderlich"
        )

    if home_goals < 0 or away_goals < 0:
        raise HTTPException(
            status_code=400,
            detail="Tore müssen >= 0 sein"
        )

    # Tiebreaker-Tracking
    tiebreaker_used = False
    tiebreaker_reason = None
    tab_used = None

    # Bei Unentschieden: Tiebreaker oder expliziter winner_id
    if home_goals == away_goals:
        if winner_id is None:
            # Automatischer Tiebreaker via Ranking
            try:
                tiebreaker_result = ranking_service.resolve_tiebreaker(
                    match.home_team_id,
                    match.away_team_id,
                    db
                )
                winner_id = tiebreaker_result["winner_id"]
                tiebreaker_used = True
                tiebreaker_reason = tiebreaker_result["reason"]
                tab_used = tiebreaker_result["tab_used"]
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tiebreaker fehlgeschlagen: {str(e)}"
                )
        # Sonst: winner_id wurde explizit übergeben

    # Bei regulärem Sieg: winner_id automatisch berechnen
    if home_goals != away_goals:
        winner_id = match.home_team_id if home_goals > away_goals else match.away_team_id

    # Validiere winner_id
    if winner_id not in [match.home_team_id, match.away_team_id]:
        raise HTTPException(
            status_code=400,
            detail="winner_id muss einem der beiden Teams entsprechen"
        )

    # Ergebnis eintragen
    match.home_goals = home_goals
    match.away_goals = away_goals
    match.status = "played"

    # Sieger in nächstes Match weiterleiten
    if match.next_match_id:
        next_match = db.get(models.KOMatch, match.next_match_id)
        if next_match:
            if match.next_match_slot == "home":
                next_match.home_team_id = winner_id
            else:
                next_match.away_team_id = winner_id

            # Wenn beide Teams da: scheduled
            if next_match.home_team_id and next_match.away_team_id:
                next_match.status = "scheduled"

    db.commit()

    # Prüfe ob Bracket komplett
    bracket = db.query(models.KOBracket).filter(
        models.KOBracket.season_id == match.season_id,
        models.KOBracket.bracket_type == match.bracket_type
    ).first()

    if bracket:
        all_matches = db.query(models.KOMatch).filter(
            models.KOMatch.season_id == match.season_id,
            models.KOMatch.bracket_type == match.bracket_type
        ).all()

        # Alle Matches gespielt?
        if all(m.status == "played" for m in all_matches):
            bracket.status = "completed"
            db.commit()

    db.refresh(match)

    # Response
    home_team = db.get(models.Team, match.home_team_id) if match.home_team_id else None
    away_team = db.get(models.Team, match.away_team_id) if match.away_team_id else None

    response = {
        "match_id": match.id,
        "home_team": {"id": home_team.id, "name": home_team.name} if home_team else None,
        "away_team": {"id": away_team.id, "name": away_team.name} if away_team else None,
        "home_goals": match.home_goals,
        "away_goals": match.away_goals,
        "winner_id": winner_id,
        "status": match.status,
        "next_match_id": match.next_match_id
    }

    # Tiebreaker-Info anhängen falls verwendet
    if tiebreaker_used:
        response["tiebreaker_used"] = True
        response["tiebreaker_reason"] = tiebreaker_reason
        response["tab_used"] = tab_used

    return response


# ============================================================
# RANKING ENDPOINTS (Google Sheets Integration)
# ============================================================

@router.get("/ranking/team/{team_name}")
def get_team_ranking_endpoint(team_name: str, db: Session = Depends(get_db)):
    """
    Public Endpoint: Holt Ranking-Details eines Teams.

    Args:
        team_name: Name des Teams (URL-encoded)

    Returns:
        {
            "team_name": "...",
            "avg_ranking": 8.3,
            "tab_used": "TN 51",
            "found": true
        }
    """
    from urllib.parse import unquote
    team_name = unquote(team_name)

    details = ranking_service.get_team_ranking_details(team_name, db)
    return details


@router.get("/ranking/all")
def get_all_rankings(db: Session = Depends(get_db)):
    """
    Public Endpoint: Gibt komplettes Ranking-Sheet zurück.

    Returns:
        {
            "tab_used": "Erster Tab (aktuelles Ranking)",
            "teams": [
                {"teamName": "...", "avg_ranking": 473.31},
                ...
            ]
        }
    """
    teams = ranking_service.fetch_ranking_sheet(db)

    return {
        "tab_used": "Erster Tab (aktuelles Ranking)",
        "teams": teams
    }


@router.get("/seasons/{season_id}/ko-brackets/status")
def get_ko_brackets_status(season_id: int, db: Session = Depends(get_db)):
    """
    Schnelle Übersicht über KO-Bracket Status.

    Returns:
    {
        "season_id": X,
        "all_groups_completed": bool,
        "brackets_generated": bool,
        "brackets": {
            "meister": {"status": "...", "matches_played": X, "matches_total": Y},
            ...
        }
    }
    """
    # Prüfe ob alle Gruppen abgeschlossen
    groups = db.query(models.Group).filter(
        models.Group.season_id == season_id
    ).all()

    all_groups_completed = True
    for group in groups:
        matches = db.query(models.Match).filter(
            models.Match.group_id == group.id
        ).all()

        if not matches:
            all_groups_completed = False
            break

        if any(m.status != "played" for m in matches):
            all_groups_completed = False
            break

    # Prüfe ob Brackets existieren
    brackets = db.query(models.KOBracket).filter(
        models.KOBracket.season_id == season_id
    ).all()

    brackets_generated = len(brackets) > 0

    # Bracket-Details
    brackets_data = {}
    for bracket_type in ["meister", "lucky_loser", "loser"]:
        bracket = next((b for b in brackets if b.bracket_type == bracket_type), None)

        if not bracket:
            brackets_data[bracket_type] = None
            continue

        # Matches zählen
        all_matches = db.query(models.KOMatch).filter(
            models.KOMatch.season_id == season_id,
            models.KOMatch.bracket_type == bracket_type
        ).all()

        played = sum(1 for m in all_matches if m.status == "played")
        total = len(all_matches)

        brackets_data[bracket_type] = {
            "status": bracket.status,
            "matches_played": played,
            "matches_total": total
        }

    return {
        "season_id": season_id,
        "all_groups_completed": all_groups_completed,
        "brackets_generated": brackets_generated,
        "brackets": brackets_data
    }


@router.post("/seasons/{season_id}/ko-brackets/reset")
def reset_ko_brackets(
    season_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Löscht alle KO-Brackets und KO-Matches einer Saison."""
    db.query(models.KOMatch).filter(models.KOMatch.season_id == season_id).delete()
    db.query(models.KOBracket).filter(models.KOBracket.season_id == season_id).delete()
    db.commit()
    return {"deleted": True}


@router.post("/seasons/{season_id}/ko-brackets/create-empty", status_code=201)
def create_empty_bracket(
    season_id: int,
    body: dict,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """
    Erstellt ein leeres KO-Bracket-Gerüst (ohne Team-Zuweisung).

    Body:
        bracket_type: "meister" | "lucky_loser" | "loser"
        team_count: 2, 4, 8, 16, 32
    """
    bracket_type = body.get("bracket_type")
    team_count = body.get("team_count")

    if bracket_type not in ("meister", "lucky_loser", "loser"):
        raise HTTPException(status_code=400, detail="bracket_type muss 'meister', 'lucky_loser' oder 'loser' sein")

    valid_counts = [2, 4, 8, 16, 32]
    if team_count not in valid_counts:
        raise HTTPException(status_code=400, detail=f"team_count muss einer von {valid_counts} sein")

    # Prüfe ob Bracket dieses Typs bereits existiert
    existing = db.query(models.KOBracket).filter(
        models.KOBracket.season_id == season_id,
        models.KOBracket.bracket_type == bracket_type
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Bracket '{bracket_type}' existiert bereits für diese Saison. Bitte zuerst zurücksetzen.")

    # KOBracket erstellen
    bracket = models.KOBracket(
        season_id=season_id,
        bracket_type=bracket_type,
        status="active",
        generated_at=datetime.utcnow()
    )
    db.add(bracket)
    db.flush()

    # Leeres Gerüst erstellen – gleiche Logik wie generate_rounds in ko_bracket_generator
    bracket_size = team_count
    total_rounds = int(math.log2(bracket_size))

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

    db.flush()

    # next_match_id / next_match_slot verdrahten
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
                match.next_match_slot = "home" if match.position % 2 == 1 else "away"

    db.commit()

    return {
        "bracket_id": bracket.id,
        "bracket_type": bracket_type,
        "matches_count": len(all_matches),
        "rounds": total_rounds
    }


@router.patch("/ko-matches/{match_id}/set-team")
def set_ko_match_team(
    match_id: int,
    body: dict,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Setzt ein Team in einen Home- oder Away-Slot eines KO-Matches."""
    slot = body.get("slot")
    team_id = body.get("team_id")

    if slot not in ("home", "away"):
        raise HTTPException(status_code=400, detail="slot muss 'home' oder 'away' sein")

    match = db.query(models.KOMatch).filter(models.KOMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="KO-Match nicht gefunden")

    if match.home_goals is not None:
        raise HTTPException(status_code=400, detail="Match bereits gespielt")

    if team_id is not None:
        # Validiere: Team muss zur Saison gehören
        season_team = db.query(models.SeasonTeam).filter(
            models.SeasonTeam.season_id == match.season_id,
            models.SeasonTeam.team_id == team_id
        ).first()
        if not season_team:
            raise HTTPException(status_code=400, detail="Team gehört nicht zu dieser Saison")

    if slot == "home":
        match.home_team_id = team_id
    else:
        match.away_team_id = team_id

    # Status aktualisieren
    if match.home_team_id and match.away_team_id:
        match.status = "scheduled"
    else:
        match.status = "pending"

    db.commit()
    db.refresh(match)

    home_team = db.get(models.Team, match.home_team_id) if match.home_team_id else None
    away_team = db.get(models.Team, match.away_team_id) if match.away_team_id else None

    return {
        "match_id": match.id,
        "home_team": {"id": home_team.id, "name": home_team.name} if home_team else None,
        "away_team": {"id": away_team.id, "name": away_team.name} if away_team else None,
        "status": match.status
    }


@router.patch("/ko-matches/{match_id}/set-bye")
def set_ko_match_bye(
    match_id: int,
    body: dict,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Markiert ein KO-Match als Freilos und leitet Team in nächste Runde weiter."""
    team_id = body.get("team_id")
    if not team_id:
        raise HTTPException(status_code=400, detail="team_id ist erforderlich")

    match = db.query(models.KOMatch).filter(models.KOMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="KO-Match nicht gefunden")

    if match.home_goals is not None:
        raise HTTPException(status_code=400, detail="Match bereits gespielt")

    # Validiere: Team muss zur Saison gehören
    season_team = db.query(models.SeasonTeam).filter(
        models.SeasonTeam.season_id == match.season_id,
        models.SeasonTeam.team_id == team_id
    ).first()
    if not season_team:
        raise HTTPException(status_code=400, detail="Team gehört nicht zu dieser Saison")

    match.is_bye = 1
    match.home_team_id = team_id
    match.away_team_id = None
    match.status = "played"

    # Sieger in nächste Runde weiterleiten
    if match.next_match_id:
        next_match = db.get(models.KOMatch, match.next_match_id)
        if next_match:
            if match.next_match_slot == "home":
                next_match.home_team_id = team_id
            else:
                next_match.away_team_id = team_id

    db.commit()
    db.refresh(match)

    team = db.get(models.Team, team_id)
    return {
        "match_id": match.id,
        "home_team": {"id": team.id, "name": team.name} if team else None,
        "is_bye": True,
        "status": match.status
    }
