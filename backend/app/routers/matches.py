import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..db import get_db
from ..auth import get_current_user

router = APIRouter()


@router.post("/matches/import", response_model=schemas.MatchImportResponse)
def import_matches(items: list[schemas.MatchImportItem], db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """
    Bulk-Import von Spielergebnissen (für n8n).
    Erkennt vertauschte Heim/Gast-Zuordnungen und filtert ungültige Paarungen.
    """
    if not items:
        return schemas.MatchImportResponse(imported=0, skipped=0, swapped=0, errors=[])

    # Alle Items müssen dieselbe Saison + Spieltag haben
    saison_name = items[0].Saison
    spieltag_raw = items[0].Spieltag

    # Spieltag parsen: "SP2" → 2
    m = re.match(r"SP(\d+)", spieltag_raw, re.IGNORECASE)
    if not m:
        raise HTTPException(status_code=400, detail=f"Ungültiges Spieltag-Format: {spieltag_raw}")
    matchday = int(m.group(1))

    # Saison finden (case-insensitive)
    season = db.query(models.Season).filter(
        models.Season.name.ilike(saison_name)
    ).first()
    if not season:
        raise HTTPException(status_code=404, detail=f"Saison '{saison_name}' nicht gefunden")

    # Alle scheduled Matches für diese Saison + Spieltag laden
    scheduled_matches = db.query(models.Match).filter(
        models.Match.season_id == season.id,
        models.Match.matchday == matchday,
    ).all()

    # Match-Lookup: (home_team_id, away_team_id) → Match
    match_lookup = {}
    for match in scheduled_matches:
        match_lookup[(match.home_team_id, match.away_team_id)] = match

    # Team-Name → ID Map (case-insensitive) für diese Saison
    season_teams = db.query(models.SeasonTeam).filter(
        models.SeasonTeam.season_id == season.id
    ).all()
    team_ids = [st.team_id for st in season_teams]
    teams = db.query(models.Team).filter(models.Team.id.in_(team_ids)).all()
    name_to_id = {t.name.lower(): t.id for t in teams}

    imported = 0
    skipped = 0
    swapped = 0
    errors = []

    for item in items:
        home_name = item.Heim.strip()
        away_name = item.Gast.strip()
        home_id = name_to_id.get(home_name.lower())
        away_id = name_to_id.get(away_name.lower())

        # Team nicht gefunden
        if home_id is None or away_id is None:
            skipped += 1
            errors.append(schemas.MatchImportError(heim=home_name, gast=away_name, reason="not_found"))
            continue

        home_goals = int(item.Heimtore)
        away_goals = int(item.Gasttore)
        was_swapped = False

        # Match suchen
        match = match_lookup.get((home_id, away_id))
        if not match:
            # Swap versuchen
            match = match_lookup.get((away_id, home_id))
            if match:
                home_goals, away_goals = away_goals, home_goals
                was_swapped = True

        if not match:
            # Fallback: KO-Matches durchsuchen
            ko_candidates = db.query(models.KOMatch).filter(
                models.KOMatch.season_id == season.id,
                models.KOMatch.status != "played",
                models.KOMatch.is_bye != 1,
            ).all()

            ko_match = None
            ko_swapped = False
            direct_hits = [m for m in ko_candidates if m.home_team_id == home_id and m.away_team_id == away_id]
            swap_hits = [m for m in ko_candidates if m.home_team_id == away_id and m.away_team_id == home_id]

            if len(direct_hits) + len(swap_hits) > 1:
                skipped += 1
                errors.append(schemas.MatchImportError(heim=home_name, gast=away_name, reason="ambiguous_ko_match"))
                continue
            elif direct_hits:
                ko_match = direct_hits[0]
            elif swap_hits:
                ko_match = swap_hits[0]
                home_goals, away_goals = away_goals, home_goals
                ko_swapped = True

            if not ko_match:
                skipped += 1
                errors.append(schemas.MatchImportError(heim=home_name, gast=away_name, reason="no_match"))
                continue

            # KO-Ergebnis eintragen
            ko_match.home_goals = home_goals
            ko_match.away_goals = away_goals
            ko_match.status = "played"

            # Sieger-Weiterleitung (nur bei klarem Sieger)
            if home_goals != away_goals:
                winner_id = ko_match.home_team_id if home_goals > away_goals else ko_match.away_team_id
                if ko_match.next_match_id:
                    next_match = db.get(models.KOMatch, ko_match.next_match_id)
                    if next_match:
                        if ko_match.next_match_slot == "home":
                            next_match.home_team_id = winner_id
                        else:
                            next_match.away_team_id = winner_id
                        if next_match.home_team_id and next_match.away_team_id:
                            next_match.status = "scheduled"

                # Verlierer-Weiterleitung ins Platz-3-Spiel
                if ko_match.loser_next_match_id:
                    loser_id = ko_match.away_team_id if winner_id == ko_match.home_team_id else ko_match.home_team_id
                    if loser_id:
                        third_place_match = db.get(models.KOMatch, ko_match.loser_next_match_id)
                        if third_place_match:
                            if ko_match.loser_next_match_slot == "home":
                                third_place_match.home_team_id = loser_id
                            else:
                                third_place_match.away_team_id = loser_id
                            if third_place_match.home_team_id and third_place_match.away_team_id:
                                third_place_match.status = "scheduled"

            imported += 1
            if ko_swapped:
                swapped += 1
            continue

        if match.status == "played":
            skipped += 1
            errors.append(schemas.MatchImportError(heim=home_name, gast=away_name, reason="already_played"))
            continue

        # Ergebnis eintragen
        match.home_goals = home_goals
        match.away_goals = away_goals
        match.status = "played"

        imported += 1
        if was_swapped:
            swapped += 1

    db.commit()

    return schemas.MatchImportResponse(
        imported=imported,
        skipped=skipped,
        swapped=swapped,
        errors=errors,
    )


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


@router.patch("/matches/bulk-update")
def bulk_update_matches(
    payload: schemas.MatchBulkUpdateRequest,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Mehrere Match-Ergebnisse auf einmal eintragen."""
    updated = 0
    errors = []

    for item in payload.matches:
        match = db.get(models.Match, item.match_id)
        if not match:
            errors.append(f"Match {item.match_id} nicht gefunden")
            continue

        match.home_goals = item.home_goals
        match.away_goals = item.away_goals
        if item.ingame_week is not None:
            match.ingame_week = item.ingame_week
        if match.status == "scheduled":
            match.status = "played"
        updated += 1

    db.commit()
    return {"updated": updated, "errors": errors}


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


def generate_round_robin(db: Session, group_id: int, season_id: int, start_week: int | None = None):
    """
    Hilfsfunktion: Generiert Round-Robin-Spielplan für eine Gruppe.
    Kann von sync-Endpoint und HTTP-Endpoint genutzt werden.
    start_week: Ingame-Startwoche (z.B. 39). ingame_week = start_week + matchday - 1.
    Gibt dict mit group_id, matches_created, matchdays zurück.
    """
    team_ids = [
        st.team_id
        for st in db.query(models.SeasonTeam)
        .filter(models.SeasonTeam.group_id == group_id)
        .all()
    ]

    if len(team_ids) < 2:
        return {"group_id": group_id, "matches_created": 0, "matchdays": 0}

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
                matchday=matchday_num,
                ingame_week=start_week + matchday_num - 1 if start_week else None
            )
            db.add(m)
            created.append(m)

    return {"group_id": group_id, "matches_created": len(created), "matchdays": len(matchdays)}


@router.post("/groups/{group_id}/generate-schedule")
def generate_group_schedule(group_id: int, start_week: int = 39, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
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
    result = generate_round_robin(db, group_id, group.season_id, start_week=start_week)
    db.commit()
    return result


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

    team_ids = set()
    for m in matches:
        team_ids.add(m.home_team_id)
        team_ids.add(m.away_team_id)
    teams = {t.id: {"name": t.name, "logo_url": t.logo_url} for t in db.query(models.Team).filter(models.Team.id.in_(team_ids)).all()}

    result = []
    for match in matches:
        home_team = teams.get(match.home_team_id, {})
        away_team = teams.get(match.away_team_id, {})
        result.append({
            "id": match.id,
            "home_team_id": match.home_team_id,
            "away_team_id": match.away_team_id,
            "home_team_name": home_team.get("name", f"Team {match.home_team_id}"),
            "home_team_logo": home_team.get("logo_url"),
            "away_team_name": away_team.get("name", f"Team {match.away_team_id}"),
            "away_team_logo": away_team.get("logo_url"),
            "home_goals": match.home_goals,
            "away_goals": match.away_goals,
            "status": match.status
        })

    return result
