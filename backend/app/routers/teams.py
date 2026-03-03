from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..auth import get_current_user

router = APIRouter()


@router.get("/teams")
def list_all_teams(
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Alle Teams mit Saison-Teilnahmen und Discord-Verknüpfung."""
    query = db.query(models.Team)
    if search and len(search.strip()) >= 2:
        query = query.filter(models.Team.name.ilike(f"%{search}%"))
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
            "participating_next": profile.participating_next if profile else False,
            "discord_user": {
                "discord_id": profile.discord_id,
                "discord_username": profile.discord_username,
            } if profile else None,
            "seasons": seasons_map.get(t.id, []),
        })

    return result


# WICHTIG: /teams/search MUSS vor /teams/{team_id} registriert werden!
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
