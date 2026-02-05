from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, schemas
from .db import SessionLocal, engine
from .auth import get_current_user, verify_credentials, create_jwt_token

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


@router.get("/teams/{team_id}", response_model=schemas.TeamDetail)
def get_team_detail(team_id: int, db: Session = Depends(get_db)):
    """Holt Team-Details mit letzten 5 Spielen"""
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Alle Matches des Teams (Gruppenphase + KO)
    group_matches = db.query(models.Match).filter(
        (models.Match.home_team_id == team_id) | (models.Match.away_team_id == team_id)
    ).order_by(models.Match.id.desc()).limit(5).all()

    ko_matches = db.query(models.KOMatch).filter(
        (models.KOMatch.home_team_id == team_id) | (models.KOMatch.away_team_id == team_id)
    ).order_by(models.KOMatch.id.desc()).limit(5).all()

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

    # Nur die letzten 5
    recent_matches = sorted(all_matches, key=lambda x: x.id, reverse=True)[:5]

    # Statistiken berechnen
    wins = sum(1 for m in recent_matches if m.result == "win")
    draws = sum(1 for m in recent_matches if m.result == "draw")
    losses = sum(1 for m in recent_matches if m.result == "loss")

    return schemas.TeamDetail(
        id=team.id,
        name=team.name,
        logo_url=team.logo_url,
        onlineliga_url=team.onlineliga_url,
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