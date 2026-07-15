import os
import random
import hashlib
import aiofiles
from math import ceil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..auth import get_current_user
from ..image_utils import validate_image_file, process_crest_image
from .matches import generate_round_robin

router = APIRouter()


def _crests_dir() -> str:
    """Upload-Verzeichnis für Wappen (env, zur Laufzeit gelesen -> testbar)."""
    upload_dir = os.getenv("UPLOAD_DIR", "/app/uploads")
    crests_dir = os.path.join(upload_dir, "crests")
    os.makedirs(crests_dir, exist_ok=True)
    return crests_dir


# Zeichen, die aus einem HTML-Attributwert ausbrechen könnten.
_CREST_URL_FORBIDDEN = set('"\'<>`')


def validate_crest_url(url: str) -> None:
    """Validiert eine vom Admin gesetzte Wappen-URL.

    Nur http(s):// oder /uploads/… erlaubt; keine Zeichen, die aus dem
    <img src>-Attribut ausbrechen (crestImg interpoliert ungeescaped).
    Wirft HTTPException(400) bei ungültigem Wert.
    """
    value = (url or "").strip()
    if not value:
        raise HTTPException(status_code=400, detail="Leere Wappen-URL; zum Entfernen DELETE nutzen")
    if any(c in _CREST_URL_FORBIDDEN for c in value):
        raise HTTPException(status_code=400, detail="Wappen-URL enthält unerlaubte Zeichen")
    if any(c.isspace() for c in value):
        raise HTTPException(status_code=400, detail="Wappen-URL darf keine Leerzeichen enthalten")
    if not (value.startswith("http://") or value.startswith("https://") or value.startswith("/uploads/")):
        raise HTTPException(
            status_code=400,
            detail="Wappen-URL muss mit http://, https:// oder /uploads/ beginnen",
        )


def _get_team_or_404(db: Session, team_id: int) -> models.Team:
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def _active_profile_for_team(db: Session, team_id: int) -> Optional[models.UserProfile]:
    return db.query(models.UserProfile).filter(
        models.UserProfile.team_id == team_id,
        models.UserProfile.is_active == True,
    ).first()


@router.get("/teams")
def list_all_teams(
    search: Optional[str] = None,
    participating: Optional[bool] = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db)
):
    """Alle Teams mit Saison-Teilnahmen und Discord-Verknüpfung.

    participating=true: Nur Teams die als 'Dabei' markiert sind (Team.participating_next).
    include_inactive=true: Auch inaktive Teams anzeigen.
    """
    query = db.query(models.Team)

    if not include_inactive:
        query = query.filter(models.Team.is_active == True)

    if search and len(search.strip()) >= 2:
        query = query.filter(models.Team.name.ilike(f"%{search}%"))

    if participating is True:
        query = query.filter(models.Team.participating_next == True)

    query = query.order_by(models.Team.name)
    teams = query.all()

    team_ids = [t.id for t in teams]

    # Saison-Teilnahmen laden
    season_teams = db.query(
        models.SeasonTeam, models.Season, models.Group
    ).join(
        models.Season, models.SeasonTeam.season_id == models.Season.id
    ).outerjoin(
        models.Group, models.SeasonTeam.group_id == models.Group.id
    ).filter(
        models.SeasonTeam.team_id.in_(team_ids)
    ).all() if team_ids else []

    # Discord-Verknüpfungen laden
    profiles = db.query(models.UserProfile).filter(
        models.UserProfile.team_id.in_(team_ids)
    ).all() if team_ids else []
    profile_map = {p.team_id: p for p in profiles}

    # Saison-Map aufbauen
    seasons_map = {}
    for st, season, group in season_teams:
        seasons_map.setdefault(st.team_id, []).append({
            "season_id": season.id,
            "season_name": season.name,
            "group_name": group.name if group else None,
            "status": season.status,
        })

    result = []
    for t in teams:
        profile = profile_map.get(t.id)
        result.append({
            "id": t.id,
            "name": t.name,
            "logo_url": t.logo_url,
            "onlineliga_url": t.onlineliga_url,
            "participating_next": t.participating_next,
            "is_active": t.is_active,
            "discord_user": {
                "discord_id": profile.discord_id,
                "discord_username": profile.discord_username,
                "crest_url": profile.crest_url,
            } if profile else None,
            "seasons": seasons_map.get(t.id, []),
        })

    return result


@router.post("/teams/bulk-register", response_model=schemas.BulkRegisterResponse)
def bulk_register_teams(
    payload: schemas.BulkRegisterPayload,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """
    Bulk-Registrierung: Teamnamen-Liste → existierende Teams als 'Dabei' markieren,
    neue Teams anlegen mit participating_next=True.
    """
    created = 0
    updated = 0

    for name in payload.teams:
        name = name.strip()
        if not name:
            continue

        existing = db.query(models.Team).filter(models.Team.name == name).first()
        if existing:
            if not existing.participating_next:
                existing.participating_next = True
                updated += 1
        else:
            team = models.Team(name=name, participating_next=True)
            db.add(team)
            created += 1

    db.commit()
    return schemas.BulkRegisterResponse(
        created=created,
        updated=updated,
        total=created + updated
    )


# WICHTIG: /teams/search und /teams/crests MÜSSEN vor /teams/{team_id} registriert werden!
@router.get("/teams/crests")
def get_team_crests(db: Session = Depends(get_db)):
    """Gibt team_id → crest_url Mapping für alle Teams mit Wappen."""
    # 1. Team.logo_url als Basis
    crests = {}
    teams_with_logo = db.query(
        models.Team.id,
        models.Team.logo_url
    ).filter(models.Team.logo_url.isnot(None)).all()
    for t in teams_with_logo:
        crests[str(t.id)] = t.logo_url

    # 2. UserProfile.crest_url überschreibt (höhere Priorität).
    # Nur aktive Profile (konsistent mit get_team_detail): ein soft-gelöschtes
    # Profil darf kein bereits entferntes Wappen wieder einblenden.
    profiles = db.query(
        models.UserProfile.team_id,
        models.UserProfile.crest_url
    ).filter(
        models.UserProfile.team_id.isnot(None),
        models.UserProfile.crest_url.isnot(None),
        models.UserProfile.is_active == True
    ).all()
    for p in profiles:
        crests[str(p.team_id)] = p.crest_url

    return crests


@router.get("/teams/search", response_model=list[schemas.TeamRead])
def search_teams(
    name: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Sucht Teams nach Name (case-insensitive, partial match).
    Unterstützt sowohl ?name= (Discord Bot) als auch ?search= (Admin-Panel).
    """
    query_str = search or name
    if not query_str or len(query_str.strip()) < 2:
        raise HTTPException(
            status_code=400,
            detail="Suchbegriff muss mindestens 2 Zeichen lang sein"
        )

    teams = db.query(models.Team).filter(
        models.Team.name.ilike(f"%{query_str}%")
    ).limit(limit).all()

    return [{"id": t.id, "name": t.name} for t in teams]


@router.get("/teams/{team_id}", response_model=schemas.TeamDetail)
def get_team_detail(team_id: int, db: Session = Depends(get_db)):
    """Holt Team-Details mit letzten 5 Spielen"""
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    group_matches = db.query(models.Match).filter(
        (models.Match.home_team_id == team_id) | (models.Match.away_team_id == team_id)
    ).order_by(models.Match.id.desc()).all()

    ko_matches = db.query(models.KOMatch).filter(
        (models.KOMatch.home_team_id == team_id) | (models.KOMatch.away_team_id == team_id)
    ).order_by(models.KOMatch.id.desc()).all()

    _team_ids = set()
    _season_ids = set()
    for m in group_matches:
        _team_ids.update([m.home_team_id, m.away_team_id])
        _season_ids.add(m.season_id)
    for m in ko_matches:
        if m.home_team_id: _team_ids.add(m.home_team_id)
        if m.away_team_id: _team_ids.add(m.away_team_id)
        _season_ids.add(m.season_id)
    teams_map = {t.id: t for t in db.query(models.Team).filter(models.Team.id.in_(_team_ids)).all()} if _team_ids else {}
    seasons_map = {s.id: s for s in db.query(models.Season).filter(models.Season.id.in_(_season_ids)).all()} if _season_ids else {}

    all_matches = []

    for m in group_matches:
        is_home = m.home_team_id == team_id
        opponent_id = m.away_team_id if is_home else m.home_team_id
        opponent = teams_map.get(opponent_id)
        season = seasons_map.get(m.season_id)

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
                opponent = teams_map.get(opponent_id)
                season = seasons_map.get(m.season_id)

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

    all_matches_sorted = sorted(all_matches, key=lambda x: x.id, reverse=True)
    wins = sum(1 for m in all_matches_sorted if m.result == "win")
    draws = sum(1 for m in all_matches_sorted if m.result == "draw")
    losses = sum(1 for m in all_matches_sorted if m.result == "loss")

    recent_matches = all_matches_sorted[:5]

    discord_profile = db.query(models.UserProfile).filter(
        models.UserProfile.team_id == team_id,
        models.UserProfile.is_active == True
    ).first()

    return schemas.TeamDetail(
        id=team.id,
        name=team.name,
        logo_url=team.logo_url,
        onlineliga_url=team.onlineliga_url,
        is_active=team.is_active,
        discord_claimed=discord_profile is not None,
        discord_username=discord_profile.discord_username if discord_profile else None,
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

    fields_set = update.model_fields_set

    if update.name is not None:
        team.name = update.name
    # logo_url ist explizit löschbar: wird das Feld mitgeschickt (auch als
    # null/""), setzen wir es. Leerstring -> None, damit /teams/crests
    # (Filter logo_url IS NOT NULL) es nicht als leeres Wappen ausliefert.
    if "logo_url" in fields_set:
        team.logo_url = update.logo_url or None
    if update.onlineliga_url is not None:
        team.onlineliga_url = update.onlineliga_url
    if update.participating_next is not None:
        team.participating_next = update.participating_next
    if update.is_active is not None:
        team.is_active = update.is_active
        if not update.is_active:
            team.participating_next = False

    db.commit()
    db.refresh(team)
    return team


# ---------- Admin-Wappenverwaltung (UserProfile.crest_url) ----------
# Das per-Owner hochgeladene Wappen überschreibt in /teams/crests die
# Team.logo_url. Diese Endpoints geben dem Admin Kontrolle darüber, um
# falsche/missbräuchliche Uploads zu korrigieren.

@router.put("/admin/teams/{team_id}/crest", response_model=schemas.AdminCrestResponse)
def admin_set_team_crest_url(
    team_id: int,
    body: schemas.AdminCrestUrlSet,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """Setzt das Wappen eines Teams per Direkt-URL (auf der aktiven UserProfile)."""
    _get_team_or_404(db, team_id)
    validate_crest_url(body.crest_url)

    profile = _active_profile_for_team(db, team_id)
    if not profile:
        raise HTTPException(
            status_code=400,
            detail="Kein verknüpfter Discord-User; nutze stattdessen die Logo-URL des Teams",
        )

    profile.crest_url = body.crest_url.strip()
    db.commit()
    return schemas.AdminCrestResponse(crest_url=profile.crest_url, message="Wappen gesetzt")


@router.post("/admin/teams/{team_id}/crest", response_model=schemas.AdminCrestResponse)
async def admin_upload_team_crest(
    team_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """Lädt ein Wappen für ein Team hoch (verarbeitet zu WebP, auf aktiver UserProfile)."""
    _get_team_or_404(db, team_id)

    profile = _active_profile_for_team(db, team_id)
    if not profile:
        raise HTTPException(
            status_code=400,
            detail="Kein verknüpfter Discord-User; nutze stattdessen die Logo-URL des Teams",
        )

    file_content = await file.read()
    is_valid, error_msg = validate_image_file(file.filename, file.content_type, len(file_content))
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        processed = await process_crest_image(file_content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    filename = f"{profile.discord_id}.webp"
    filepath = os.path.join(_crests_dir(), filename)
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(processed)

    # Cache-Busting: Content-Hash als ?v=, damit der Austausch sofort sichtbar
    # ist (gleicher Dateiname würde sonst aus Browser-/CDN-Cache kommen).
    version = hashlib.sha256(processed).hexdigest()[:8]
    profile.crest_url = f"/uploads/crests/{filename}?v={version}"
    db.commit()
    return schemas.AdminCrestResponse(crest_url=profile.crest_url, message="Wappen hochgeladen")


@router.delete("/admin/teams/{team_id}/crest", response_model=schemas.AdminCrestResponse)
def admin_delete_team_crest(
    team_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """Löscht das hochgeladene Wappen eines Teams -> Fallback auf Team.logo_url."""
    _get_team_or_404(db, team_id)

    # Anzeige/Löschen darf auch eine inaktive Profile mit crest_url treffen
    # (verwaiste Overrides bleiben entfernbar).
    profile = _active_profile_for_team(db, team_id)
    if not profile or not profile.crest_url:
        profile = db.query(models.UserProfile).filter(
            models.UserProfile.team_id == team_id,
            models.UserProfile.crest_url.isnot(None),
        ).first()
    if not profile or not profile.crest_url:
        raise HTTPException(status_code=404, detail="Kein Wappen vorhanden")

    # Lokale Upload-Datei mitentfernen (externe URLs: nur DB-Feld leeren).
    path_part = profile.crest_url.split("?", 1)[0]
    if path_part.startswith("/uploads/crests/"):
        filepath = os.path.join(_crests_dir(), os.path.basename(path_part))
        if os.path.exists(filepath):
            os.remove(filepath)

    profile.crest_url = None
    db.commit()
    return schemas.AdminCrestResponse(crest_url=None, message="Wappen gelöscht")


@router.put("/seasons/{season_id}/teams/sync")
def sync_season_teams(
    season_id: int,
    payload: schemas.SyncTeamsPayload,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """
    Diff-basierter Team-Sync: Nimmt Team-IDs + Seeding-Info,
    synchronisiert SeasonTeam-Einträge, berechnet Gruppen neu,
    generiert optional Spielplan.
    """
    from .matches import generate_round_robin

    season = db.query(models.Season).filter(models.Season.id == season_id).first()
    if not season:
        raise HTTPException(status_code=404, detail="Season not found")

    # 1. Bestehende team_ids laden
    existing_sts = db.query(models.SeasonTeam).filter(
        models.SeasonTeam.season_id == season_id
    ).all()
    existing_ids = {st.team_id for st in existing_sts}
    desired_ids = set(payload.team_ids)

    # 2. Diff
    to_add = desired_ids - existing_ids
    to_remove = existing_ids - desired_ids

    # 3. Entfernen: SeasonTeam + zugehörige ungespielte Matches
    if to_remove:
        # Ungespielte Matches löschen wo ein entferntes Team beteiligt ist
        db.query(models.Match).filter(
            models.Match.season_id == season_id,
            models.Match.status == "scheduled",
            (models.Match.home_team_id.in_(to_remove) | models.Match.away_team_id.in_(to_remove))
        ).delete(synchronize_session="fetch")

        db.query(models.SeasonTeam).filter(
            models.SeasonTeam.season_id == season_id,
            models.SeasonTeam.team_id.in_(to_remove)
        ).delete(synchronize_session="fetch")

    # 4. Gruppen anpassen: ceil(len / 4)
    final_team_ids = list(desired_ids)
    needed_groups = ceil(len(final_team_ids) / 4) if final_team_ids else 0
    group_names = list("ABCDEFGHIJKLMNOP")

    existing_groups = db.query(models.Group).filter(
        models.Group.season_id == season_id
    ).order_by(models.Group.sort_order).all()

    # Überschüssige leere Gruppen löschen
    while len(existing_groups) > needed_groups:
        g = existing_groups.pop()
        # Nur löschen wenn keine gespielten Matches drin
        played = db.query(models.Match).filter(
            models.Match.group_id == g.id,
            models.Match.status != "scheduled"
        ).count()
        if played == 0:
            db.query(models.Match).filter(models.Match.group_id == g.id).delete()
            db.query(models.SeasonTeam).filter(models.SeasonTeam.group_id == g.id).update(
                {models.SeasonTeam.group_id: None}, synchronize_session="fetch"
            )
            db.delete(g)
        else:
            existing_groups.append(g)
            break

    # Fehlende Gruppen erstellen
    while len(existing_groups) < needed_groups:
        idx = len(existing_groups)
        g = models.Group(
            season_id=season_id,
            name=group_names[idx] if idx < len(group_names) else f"G{idx+1}",
            sort_order=idx
        )
        db.add(g)
        db.flush()
        existing_groups.append(g)

    # 5. Alle Teams auf Gruppen verteilen (Seeded zuerst, Rest zufällig)
    # Alle bestehenden group_id Zuordnungen zurücksetzen
    db.query(models.SeasonTeam).filter(
        models.SeasonTeam.season_id == season_id
    ).update({models.SeasonTeam.group_id: None}, synchronize_session="fetch")

    # Neue Teams hinzufügen
    for tid in to_add:
        team = db.query(models.Team).filter(models.Team.id == tid).first()
        if not team:
            continue
        st = models.SeasonTeam(season_id=season_id, team_id=tid, group_id=None)
        db.add(st)
    db.flush()

    # Season participant_count aktualisieren
    season.participant_count = len(final_team_ids)

    # Gruppen-Map: name -> group
    group_map = {g.name: g for g in existing_groups}

    # Seeded Teams zuerst platzieren
    seeded_team_ids = set()
    group_assignments = {g.id: [] for g in existing_groups}

    for group_name, team_id in payload.seeded_teams.items():
        if team_id in desired_ids and group_name in group_map:
            group = group_map[group_name]
            group_assignments[group.id].append(team_id)
            seeded_team_ids.add(team_id)

    # Rest zufällig gleichmäßig verteilen
    unseeded = [tid for tid in final_team_ids if tid not in seeded_team_ids]
    random.shuffle(unseeded)

    for tid in unseeded:
        # Gruppe mit wenigsten Teams
        min_group_id = min(group_assignments, key=lambda gid: len(group_assignments[gid]))
        group_assignments[min_group_id].append(tid)

    # SeasonTeam group_id setzen
    for group_id, team_ids in group_assignments.items():
        for tid in team_ids:
            db.query(models.SeasonTeam).filter(
                models.SeasonTeam.season_id == season_id,
                models.SeasonTeam.team_id == tid
            ).update({models.SeasonTeam.group_id: group_id}, synchronize_session="fetch")

    # 6. Spielplan generieren
    schedule_results = []
    if payload.generate_schedule:
        for g in existing_groups:
            # Bestehende scheduled Matches löschen
            db.query(models.Match).filter(
                models.Match.group_id == g.id,
                models.Match.status == "scheduled"
            ).delete(synchronize_session="fetch")
            result = generate_round_robin(db, g.id, season_id)
            schedule_results.append(result)

    db.commit()

    # Response
    groups_out = []
    for g in existing_groups:
        teams_in_group = db.query(models.SeasonTeam).filter(
            models.SeasonTeam.group_id == g.id,
            models.SeasonTeam.season_id == season_id
        ).all()
        team_objs = db.query(models.Team).filter(
            models.Team.id.in_([st.team_id for st in teams_in_group])
        ).all() if teams_in_group else []
        groups_out.append({
            "id": g.id,
            "name": g.name,
            "teams": [{"id": t.id, "name": t.name} for t in team_objs]
        })

    return {
        "season_id": season_id,
        "groups": groups_out,
        "added": len(to_add),
        "removed": len(to_remove),
        "schedule": schedule_results
    }


@router.post("/seasons/{season_id}/teams", response_model=schemas.TeamRead)
def add_team_to_season(season_id: int, team: schemas.TeamCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    existing_team = db.query(models.Team).filter(models.Team.name == team.name).first()

    if existing_team:
        t = existing_team
    else:
        t = models.Team(
            name=team.name,
            logo_url=team.logo_url,
            onlineliga_url=team.onlineliga_url
        )
        db.add(t)
        db.commit()
        db.refresh(t)

    if team.group_id is not None:
        target_group_id = team.group_id
        group = db.query(models.Group).filter(
            models.Group.id == target_group_id,
            models.Group.season_id == season_id
        ).first()
        if not group:
            raise HTTPException(status_code=400, detail=f"Group {target_group_id} not found in season {season_id}")
    else:
        groups = db.query(models.Group).filter(models.Group.season_id == season_id).order_by(models.Group.sort_order).all()
        counts = {g.id: db.query(models.SeasonTeam).filter(models.SeasonTeam.group_id == g.id).count() for g in groups}
        target_group_id = min(counts, key=counts.get)

    existing_st = db.query(models.SeasonTeam).filter_by(season_id=season_id, team_id=t.id).first()
    if existing_st:
        raise HTTPException(status_code=400, detail=f"Team '{t.name}' ist bereits in dieser Saison")

    st = models.SeasonTeam(season_id=season_id, team_id=t.id, group_id=target_group_id)
    db.add(st)
    db.commit()

    return t


@router.post("/seasons/{season_id}/teams/bulk")
def bulk_add_teams(season_id: int, payload: schemas.BulkTeamCreate, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    groups = db.query(models.Group).filter(models.Group.season_id == season_id).order_by(models.Group.sort_order).all()
    if not groups:
        raise HTTPException(status_code=400, detail="No groups for season")

    counts = {g.id: db.query(models.SeasonTeam).filter(models.SeasonTeam.group_id == g.id).count() for g in groups}

    created = []
    for name in payload.teams:
        existing_team = db.query(models.Team).filter(models.Team.name == name).first()

        if existing_team:
            t = existing_team
        else:
            t = models.Team(name=name)
            db.add(t)
            db.flush()

        existing_st = db.query(models.SeasonTeam).filter_by(season_id=season_id, team_id=t.id).first()
        if existing_st:
            continue

        target_group_id = min(counts, key=counts.get)

        st = models.SeasonTeam(season_id=season_id, team_id=t.id, group_id=target_group_id)
        db.add(st)

        counts[target_group_id] += 1

        created.append({"id": t.id, "name": t.name, "group_id": target_group_id})

    db.commit()
    return {
        "created": created,
        "count": len(created)
    }


def _assign_latecomer(db: Session, season_id: int, group_id: int, team_id: int):
    """Weist ein Pool-Team einer unvollständigen Gruppe zu und regeneriert
    den Spielplan dieser Gruppe. Wirft HTTPException bei Verstößen.
    Saisonweite Sperre: kein Match der Saison darf bereits gespielt sein.
    """
    # 1. Saison existiert + saisonweite Sperre
    season = db.get(models.Season, season_id)
    if not season:
        raise HTTPException(status_code=404, detail="SAISON_NICHT_GEFUNDEN")
    locked = db.query(models.Match).filter(
        models.Match.season_id == season_id,
        models.Match.status != "scheduled",
    ).first()
    if locked:
        raise HTTPException(status_code=409, detail="SAISON_GESPERRT")

    # 2. Gruppe gehört zur Saison
    group = db.query(models.Group).filter(
        models.Group.id == group_id,
        models.Group.season_id == season_id,
    ).first()
    if not group:
        raise HTTPException(status_code=404, detail="GRUPPE_NICHT_GEFUNDEN")

    # 3. Kapazität (< 4)
    count = db.query(models.SeasonTeam).filter(
        models.SeasonTeam.group_id == group_id
    ).count()
    if count >= 4:
        raise HTTPException(status_code=409, detail="GRUPPE_VOLL")

    # 4. Team aus Anmelde-Pool, noch nicht in Saison
    team = db.get(models.Team, team_id)
    if not team or not team.participating_next:
        raise HTTPException(status_code=400, detail="TEAM_UNGUELTIG")
    existing_st = db.query(models.SeasonTeam).filter_by(
        season_id=season_id, team_id=team_id
    ).first()
    if existing_st:
        raise HTTPException(status_code=400, detail="TEAM_BEREITS_IN_SAISON")

    # 5. Zuweisen
    db.add(models.SeasonTeam(season_id=season_id, team_id=team_id, group_id=group_id))
    db.flush()

    # 6. Spielplan nur dieser Gruppe regenerieren, Ingame-Startwoche erhalten
    existing_matches = db.query(models.Match).filter(
        models.Match.group_id == group_id
    ).all()
    ingame_weeks = [m.ingame_week for m in existing_matches if m.ingame_week is not None]
    start_week = min(ingame_weeks) if ingame_weeks else None
    db.query(models.Match).filter(
        models.Match.group_id == group_id
    ).delete(synchronize_session="fetch")
    result = generate_round_robin(db, group_id, season_id, start_week=start_week)

    # 7. participant_count
    season.participant_count = (season.participant_count or 0) + 1

    db.commit()

    teams = (
        db.query(models.Team)
        .join(models.SeasonTeam, models.SeasonTeam.team_id == models.Team.id)
        .filter(models.SeasonTeam.group_id == group_id)
        .all()
    )
    return {
        "group_id": group_id,
        "teams": [{"id": t.id, "name": t.name} for t in teams],
        "matches_created": result["matches_created"],
    }


@router.post("/seasons/{season_id}/groups/{group_id}/assign-latecomer")
def assign_latecomer(
    season_id: int,
    group_id: int,
    payload: schemas.AssignLatecomerPayload,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user),
):
    """Weist ein Pool-Team (participating_next) einer unvollständigen Gruppe zu,
    solange die Saison noch nicht gespielt wurde. Regeneriert den Gruppen-Spielplan.
    """
    return _assign_latecomer(db, season_id, group_id, payload.team_id)
