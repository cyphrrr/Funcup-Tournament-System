from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from .. import models
from ..db import get_db
from ..auth import get_current_user

router = APIRouter()


@router.get("/admin/anmeldungen")
def get_anmeldungen(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Admin-Endpoint: Alle Discord User mit Anmeldestatus."""
    users = db.query(models.UserProfile).options(selectinload(models.UserProfile.team)).all()

    result = []
    for user in users:
        team_name = user.team.name if user.team else None

        has_profile = bool(user.profile_url and user.profile_url.strip())
        is_complete = (
            has_profile
            and user.team_id is not None
            and user.participating_next is True
        )

        result.append({
            "discord_id": user.discord_id,
            "discord_username": user.discord_username,
            "team_id": user.team_id,
            "team_name": team_name,
            "profile_url": user.profile_url,
            "has_profile": has_profile,
            "participating_next": user.participating_next or False,
            "is_complete": is_complete,
        })

    result.sort(key=lambda x: (not x["is_complete"], x["discord_username"].lower()))
    return result


@router.post("/admin/anmeldungen/{discord_id}/season")
def add_to_season(
    discord_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Fügt User-Team zur aktiven Saison hinzu (kleinste Gruppe)."""
    season = db.query(models.Season).filter(
        models.Season.status.in_(["active", "planned"])
    ).order_by(models.Season.id.desc()).first()
    if not season:
        raise HTTPException(status_code=404, detail="Keine aktive Saison gefunden")

    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    if not user.team_id:
        raise HTTPException(status_code=400, detail="User hat kein Team zugewiesen")

    existing = db.query(models.SeasonTeam).filter(
        models.SeasonTeam.season_id == season.id,
        models.SeasonTeam.team_id == user.team_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Team bereits in aktiver Saison")

    groups = db.query(models.Group).filter(models.Group.season_id == season.id).all()
    if not groups:
        raise HTTPException(status_code=400, detail="Keine Gruppen in aktiver Saison")

    group_sizes = {}
    for g in groups:
        count = db.query(models.SeasonTeam).filter(
            models.SeasonTeam.group_id == g.id
        ).count()
        group_sizes[g.id] = count

    smallest_group_id = min(group_sizes, key=group_sizes.get)

    st = models.SeasonTeam(
        season_id=season.id,
        team_id=user.team_id,
        group_id=smallest_group_id
    )
    db.add(st)
    db.commit()
    db.refresh(st)

    return {"ok": True, "season_team_id": st.id}


@router.delete("/admin/anmeldungen/{discord_id}/season")
def remove_from_season(
    discord_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Entfernt User-Team aus der aktiven Saison."""
    season = db.query(models.Season).filter(
        models.Season.status.in_(["active", "planned"])
    ).order_by(models.Season.id.desc()).first()
    if not season:
        raise HTTPException(status_code=404, detail="Keine aktive Saison gefunden")

    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")
    if not user.team_id:
        raise HTTPException(status_code=400, detail="User hat kein Team")

    st = db.query(models.SeasonTeam).filter(
        models.SeasonTeam.season_id == season.id,
        models.SeasonTeam.team_id == user.team_id
    ).first()
    if not st:
        raise HTTPException(status_code=404, detail="Team nicht in aktiver Saison")

    db.delete(st)
    db.commit()
    return {"ok": True}
