from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..auth import get_current_user

router = APIRouter()


@router.post("/seasons", response_model=schemas.SeasonRead)
def create_season(season: schemas.SeasonCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    obj = models.Season(
        name=season.name,
        participant_count=season.participant_count,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)

    if season.group_count is not None and season.group_count > 0:
        group_count = season.group_count
    else:
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

    if update.status is not None and update.status != season.status:
        valid_transitions = {
            "planned": ["active"],
            "active": ["archived"],
            "archived": []
        }
        allowed = valid_transitions.get(season.status, [])
        if update.status not in allowed:
            raise HTTPException(
                status_code=400,
                detail=f"Ungültiger Status-Übergang: '{season.status}' → '{update.status}'. Erlaubt: {allowed}"
            )
        season.status = update.status

    if update.name is not None:
        if season.status == "archived":
            raise HTTPException(status_code=400, detail="Archivierte Saisons können nicht bearbeitet werden")
        season.name = update.name

    db.commit()
    db.refresh(season)
    return season


@router.delete("/seasons/{season_id}")
def delete_season(season_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """Löscht eine Saison komplett (inkl. Gruppen, Teams, Matches)"""
    season = db.query(models.Season).filter(models.Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")

    db.query(models.KOMatch).filter(models.KOMatch.season_id == season_id).delete()
    db.query(models.KOBracket).filter(models.KOBracket.season_id == season_id).delete()
    db.query(models.Match).filter(models.Match.season_id == season_id).delete()
    db.query(models.SeasonTeam).filter(models.SeasonTeam.season_id == season_id).delete()
    db.query(models.Group).filter(models.Group.season_id == season_id).delete()
    db.delete(season)
    db.commit()

    return {"deleted": True, "id": season_id}


@router.get("/seasons/{season_id}/groups", response_model=list[schemas.GroupRead])
def list_groups(season_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.Group)
        .filter(models.Group.season_id == season_id)
        .order_by(models.Group.sort_order)
        .all()
    )


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
                    "matchday": m.matchday,
                    "ingame_week": m.ingame_week,
                }
                for m in matches
            ],
        })
    return result
