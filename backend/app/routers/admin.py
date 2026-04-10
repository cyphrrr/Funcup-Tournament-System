import csv
import requests as _requests
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models
from ..db import get_db
from ..auth import get_current_user
from ..ranking_service import SHEET_ID, get_active_tab_name, _sheet_cache

router = APIRouter()


@router.get("/admin/anmeldungen")
def get_anmeldungen(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Admin-Endpoint: Alle aktiven Teams mit Anmeldestatus und optionalem Discord-User."""
    teams = db.query(models.Team).filter(models.Team.is_active == True).order_by(models.Team.name).all()

    team_ids = [t.id for t in teams]
    profiles = db.query(models.UserProfile).filter(
        models.UserProfile.team_id.in_(team_ids),
        models.UserProfile.is_active == True
    ).all() if team_ids else []
    profile_map = {p.team_id: p for p in profiles}

    result = []
    for team in teams:
        profile = profile_map.get(team.id)
        has_profile = bool(profile and profile.profile_url and profile.profile_url.strip())
        is_complete = (
            has_profile
            and team.participating_next is True
        )

        result.append({
            "team_id": team.id,
            "team_name": team.name,
            "logo_url": team.logo_url,
            "participating_next": team.participating_next,
            "has_profile": has_profile,
            "is_complete": is_complete,
            "discord_user": {
                "discord_id": profile.discord_id,
                "discord_username": profile.discord_username,
                "profile_url": profile.profile_url,
            } if profile else None,
        })

    # Dabei zuerst, dann alphabetisch
    result.sort(key=lambda x: (not x["participating_next"], x["team_name"].lower()))
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


def _fetch_sheet_participants(db: Session) -> dict:
    """Interne Hilfsfunktion: Sheet-Teilnehmerliste mit Cache holen."""
    tab_name = get_active_tab_name(db)
    cache_key = f"sheet_participants_{tab_name}"

    if cache_key in _sheet_cache:
        cached = _sheet_cache[cache_key]
        age = (datetime.utcnow() - cached["timestamp"]).total_seconds()
        if age < 600:
            return {"tab_name": tab_name, "participants": cached["data"]}

    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export"
        f"?format=csv&sheet={_requests.utils.quote(tab_name)}"
    )

    try:
        response = _requests.get(url, timeout=15)
        response.raise_for_status()
    except _requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Google Sheet nicht erreichbar: {str(e)}"
        )

    lines = response.text.splitlines()
    reader = csv.reader(lines)
    next(reader, None)  # Header überspringen

    participants = []
    for row in reader:
        team_name = row[2].strip() if len(row) > 2 else ""
        zusage_str = row[15].strip() if len(row) > 15 else ""
        if not team_name:
            continue
        participants.append({
            "team_name": team_name,
            "zusage": zusage_str == "1",
        })

    _sheet_cache[cache_key] = {
        "data": participants,
        "timestamp": datetime.utcnow(),
    }
    return {"tab_name": tab_name, "participants": participants}


@router.get("/admin/sheet-participants")
def get_sheet_participants(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Liest Teilnehmerliste aus Google Sheet (Tab 'TN {nr}', Spalte C + P)."""
    return _fetch_sheet_participants(db)


@router.post("/admin/sheet-sync")
def sync_sheet_participants(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """
    Gleicht Google Sheet Teilnehmerliste mit DB ab.
    Legt fehlende Teams aus Sheet automatisch an (participating_next=True).
    """
    sheet_data = _fetch_sheet_participants(db)
    sheet_with_zusage = [p for p in sheet_data["participants"] if p["zusage"]]
    sheet_names = {p["team_name"].lower(): p["team_name"] for p in sheet_with_zusage}

    all_teams = db.query(models.Team).filter(models.Team.is_active == True).all()
    db_teams_by_name = {t.name.lower(): t for t in all_teams}
    dabei_teams = {t.name.lower(): t for t in all_teams if t.participating_next}

    matched = []
    only_discord = []
    only_sheet = []
    created_count = 0
    updated_count = 0

    for lower_name, original_name in sheet_names.items():
        if lower_name in dabei_teams:
            team = dabei_teams[lower_name]
            matched.append({"team_id": team.id, "team_name": team.name, "source": "both"})
        elif lower_name in db_teams_by_name:
            team = db_teams_by_name[lower_name]
            team.participating_next = True
            updated_count += 1
            matched.append({
                "team_id": team.id,
                "team_name": team.name,
                "source": "both",
                "note": "participating_next auf True gesetzt",
            })
        else:
            new_team = models.Team(
                name=original_name,
                participating_next=True,
                is_active=True,
            )
            db.add(new_team)
            db.flush()
            created_count += 1
            only_sheet.append({
                "team_id": new_team.id,
                "team_name": new_team.name,
                "source": "sheet_only",
                "note": "Neu angelegt",
            })

    for lower_name, team in dabei_teams.items():
        if lower_name not in sheet_names:
            only_discord.append({
                "team_id": team.id,
                "team_name": team.name,
                "source": "discord_only",
            })

    db.commit()

    return {
        "tab_name": sheet_data["tab_name"],
        "matched": matched,
        "only_discord": only_discord,
        "only_sheet": only_sheet,
        "created": created_count,
        "updated": updated_count,
        "total_participating": len(matched) + len(only_sheet),
    }
