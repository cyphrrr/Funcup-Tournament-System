from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..auth import get_current_user

router = APIRouter()


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

    n = len(team_ids)
    teams = team_ids.copy()

    if n % 2 == 1:
        teams.append(None)
        n += 1

    matchdays = []
    for round_num in range(n - 1):
        round_matches = []
        for i in range(n // 2):
            home = teams[i]
            away = teams[n - 1 - i]

            if home is not None and away is not None:
                round_matches.append((home, away))

        matchdays.append(round_matches)

        teams = [teams[0]] + [teams[-1]] + teams[1:-1]

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


@router.get("/seasons/{season_id}/matchdays")
def get_season_matchdays(season_id: int, db: Session = Depends(get_db)):
    """Gibt die maximale Spieltag-Nummer für eine Saison zurück."""
    from sqlalchemy import func

    max_matchday = db.query(func.max(models.Match.matchday)).filter(
        models.Match.season_id == season_id
    ).scalar()

    return {"max_matchday": max_matchday or 0}


@router.get("/seasons/{season_id}/matchday/{matchday}")
def get_season_matchday(season_id: int, matchday: int, db: Session = Depends(get_db)):
    """Holt alle Matches eines Spieltags über alle Gruppen einer Saison."""
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
    """Gibt die Anzahl der Spieltage in einer Gruppe zurück."""
    from sqlalchemy import func

    max_matchday = db.query(func.max(models.Match.matchday)).filter(
        models.Match.group_id == group_id
    ).scalar()

    return {"max_matchday": max_matchday or 0}


@router.get("/groups/{group_id}/matchday/{matchday}")
def get_group_matchday(group_id: int, matchday: int, db: Session = Depends(get_db)):
    """Holt alle Matches eines bestimmten Spieltags in einer Gruppe."""
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
