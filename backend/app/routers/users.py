import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..auth import get_current_user

router = APIRouter()


def _build_user_response(user, db: Session) -> schemas.UserProfileResponse:
    """Helper: Baut UserProfileResponse mit team_name und team_participating_next."""
    team_name = None
    team_participating_next = False
    if user.team_id:
        team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
        if team:
            team_name = team.name
            team_participating_next = team.participating_next

    return schemas.UserProfileResponse(
        id=user.id,
        discord_id=user.discord_id,
        discord_username=user.discord_username,
        discord_avatar_url=user.discord_avatar_url,
        team_id=user.team_id,
        team_name=team_name,
        profile_url=user.profile_url,
        is_active=user.is_active,
        team_participating_next=team_participating_next,
        crest_url=user.crest_url,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.post("/discord/users/ensure", response_model=schemas.UserProfileResponse)
def ensure_user(
    user_data: schemas.UserEnsureRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Upsert-Endpoint: Erstellt User falls nicht vorhanden, aktualisiert sonst username/avatar."""
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == user_data.discord_id
    ).first()

    if user:
        if user_data.discord_username is not None:
            user.discord_username = user_data.discord_username
        if user_data.discord_avatar_url is not None:
            user.discord_avatar_url = user_data.discord_avatar_url
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
    else:
        user = models.UserProfile(
            discord_id=user_data.discord_id,
            discord_username=user_data.discord_username,
            discord_avatar_url=user_data.discord_avatar_url,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    return _build_user_response(user, db)


@router.get("/discord/users/{discord_id}", response_model=schemas.UserProfileResponse)
def get_user_by_discord_id(
    discord_id: str,
    db: Session = Depends(get_db)
):
    """Holt User-Profil anhand Discord ID."""
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Kein User mit Discord ID {discord_id} gefunden"
        )

    return _build_user_response(user, db)


@router.patch("/discord/users/{discord_id}/participation", response_model=schemas.UserProfileResponse)
def update_participation(
    discord_id: str,
    update: schemas.ParticipationUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Setzt Teilnahme-Status für nächsten Pokal."""
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Kein User mit Discord ID {discord_id} gefunden"
        )

    # participating_next wird ausschließlich am Team gesetzt
    if not user.team_id:
        raise HTTPException(status_code=400, detail="KEIN_TEAM_VERKNUEPFT")

    team = db.query(models.Team).filter(models.Team.id == user.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team nicht gefunden")

    team.participating_next = update.participating

    # Auto-Reaktivierung: Wenn User sich anmeldet und Team inaktiv ist
    if update.participating and not team.is_active:
        team.is_active = True

    db.commit()
    db.refresh(user)

    return _build_user_response(user, db)


@router.patch("/discord/users/{discord_id}/profile", response_model=schemas.UserProfileResponse)
def update_profile_url(
    discord_id: str,
    update: schemas.ProfileUrlUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Speichert Onlineliga Profil-URL."""
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"Kein User mit Discord ID {discord_id} gefunden"
        )

    user.profile_url = str(update.profile_url)
    db.commit()
    db.refresh(user)

    return _build_user_response(user, db)


@router.patch("/discord/users/{discord_id}", response_model=schemas.UserProfileResponse)
def update_user_profile(
    discord_id: str,
    update_data: schemas.UserProfileAdminUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Aktualisiert ein User-Profil (Admin only)."""
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User mit Discord ID {discord_id} nicht gefunden"
        )

    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(user, field, value)

    user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return _build_user_response(user, db)


@router.patch("/discord/users/{discord_id}/team")
def assign_team_to_user(
    discord_id: str,
    update: schemas.AdminSetTeamRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Admin-Endpoint: Team einem Discord-User zuweisen."""
    team_id = update.team_id

    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="User nicht gefunden")

    if team_id is not None:
        team = db.query(models.Team).filter(models.Team.id == team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail=f"Team {team_id} nicht gefunden")

    user.team_id = team_id
    db.commit()
    db.refresh(user)

    return {
        "discord_id": user.discord_id,
        "discord_username": user.discord_username,
        "team_id": user.team_id,
        "profile_url": user.profile_url,
    }


@router.post("/discord/users/register", response_model=schemas.UserProfileResponse)
def register_discord_user(
    user_data: schemas.UserProfileCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Registriert neuen Discord User oder Non-Discord-Teilnehmer."""
    discord_id = user_data.discord_id
    if not discord_id:
        discord_id = f"no-discord-{uuid.uuid4().hex[:8]}"

    if user_data.discord_id:
        existing = db.query(models.UserProfile).filter(
            models.UserProfile.discord_id == discord_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"User mit Discord ID {discord_id} existiert bereits")

    user = models.UserProfile(
        discord_id=discord_id,
        discord_username=user_data.discord_username,
        profile_url=str(user_data.profile_url) if user_data.profile_url else None,
        team_id=user_data.team_id,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    if user_data.team_id:
        season = db.query(models.Season).filter(models.Season.status == "active").first()
        if season:
            existing_st = db.query(models.SeasonTeam).filter(
                models.SeasonTeam.season_id == season.id,
                models.SeasonTeam.team_id == user_data.team_id
            ).first()
            if not existing_st:
                groups = db.query(models.Group).filter(models.Group.season_id == season.id).all()
                if groups:
                    group_sizes = {}
                    for g in groups:
                        count = db.query(models.SeasonTeam).filter(
                            models.SeasonTeam.group_id == g.id
                        ).count()
                        group_sizes[g.id] = count
                    smallest_group_id = min(group_sizes, key=group_sizes.get)

                    st = models.SeasonTeam(
                        season_id=season.id,
                        team_id=user_data.team_id,
                        group_id=smallest_group_id
                    )
                    db.add(st)
                    db.commit()

    return _build_user_response(user, db)


@router.post("/discord/users/{discord_id}/claim-team", response_model=schemas.UserProfileResponse)
def claim_team(
    discord_id: str,
    claim_data: schemas.TeamClaimRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """User claimed ein Team (Self-Service)."""
    team_id = claim_data.team_id

    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User mit Discord ID {discord_id} nicht gefunden"
        )

    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team nicht gefunden")

    if user.team_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Du hast bereits ein Team verknüpft"
        )

    existing_claim = db.query(models.UserProfile).filter(
        models.UserProfile.team_id == team_id,
        models.UserProfile.discord_id != discord_id
    ).first()
    if existing_claim:
        raise HTTPException(
            status_code=409,
            detail="Team ist bereits von einem anderen User verknüpft"
        )

    user.team_id = team_id
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return _build_user_response(user, db)


@router.get("/discord/participation-report")
def get_participation_report(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Admin-Report: Teilnahme-Status basierend auf Teams."""
    teams = db.query(models.Team).filter(models.Team.is_active == True).all()

    total = len(teams)
    participating_count = sum(1 for t in teams if t.participating_next)
    rate = (participating_count / total * 100) if total > 0 else 0.0

    # Discord-User-Verknüpfungen laden
    team_ids = [t.id for t in teams]
    profiles = db.query(models.UserProfile).filter(
        models.UserProfile.team_id.in_(team_ids),
        models.UserProfile.is_active == True
    ).all() if team_ids else []
    profile_map = {p.team_id: p for p in profiles}

    participating_list = []
    for team in teams:
        if not team.participating_next:
            continue
        profile = profile_map.get(team.id)
        participating_list.append({
            "team_id": team.id,
            "team_name": team.name,
            "discord_user": {
                "discord_id": profile.discord_id,
                "discord_username": profile.discord_username,
            } if profile else None,
        })

    return {
        "total_teams": total,
        "participating_count": participating_count,
        "not_participating_count": total - participating_count,
        "participation_rate": round(rate, 1),
        "participating": participating_list,
    }


@router.get("/discord/users", response_model=list[schemas.UserProfileResponse])
def list_discord_users(
    search: Optional[str] = None,
    has_team: Optional[bool] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Admin-Endpoint: Liste aller Discord User mit Filteroptionen."""
    query = db.query(models.UserProfile)

    if not include_inactive:
        query = query.filter(models.UserProfile.is_active == True)

    if search:
        query = query.filter(
            models.UserProfile.discord_username.ilike(f"%{search}%")
        )

    if has_team is not None:
        if has_team:
            query = query.filter(models.UserProfile.team_id.isnot(None))
        else:
            query = query.filter(models.UserProfile.team_id.is_(None))

    users = query.order_by(models.UserProfile.created_at.desc()).all()

    user_responses = []
    for user in users:
        user_responses.append(_build_user_response(user, db))

    return user_responses


@router.delete("/discord/users/{discord_id}", response_model=schemas.UserDeleteResponse)
def delete_discord_user(
    discord_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Admin-Endpoint: Löscht einen Discord User."""
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
    _: str = Depends(get_current_user)
):
    """Admin-Endpoint: Setzt Team für User (ohne Konfliktprüfung)."""
    user = db.query(models.UserProfile).filter(
        models.UserProfile.discord_id == discord_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail=f"User mit Discord ID {discord_id} nicht gefunden"
        )

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

    user.team_id = team_data.team_id
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return _build_user_response(user, db)
