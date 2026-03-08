import math
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, ranking_service
from ..db import get_db
from ..auth import get_current_user
from ..ko_bracket_generator import generate_ko_brackets_v2, preview_ko_brackets

router = APIRouter()


def _next_power_of_two(n: int) -> int:
    return 1 << (n - 1).bit_length()


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


@router.get("/seasons/{season_id}/ko-plan", response_model=schemas.KOPlan)
def ko_plan(season_id: int, db: Session = Depends(get_db)):
    """
    Erstellt einen logischen KO-Plan (ohne Persistenz).
    Freilose werden berechnet, falls keine Zweierpotenz.
    """
    team_ids = [
        st.team_id
        for st in db.query(models.SeasonTeam)
        .filter(models.SeasonTeam.season_id == season_id)
        .all()
    ]

    if not team_ids:
        raise HTTPException(status_code=400, detail="No teams for season")

    total = len(team_ids)
    bracket_size = _next_power_of_two(total)
    byes_needed = bracket_size - total

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


@router.post("/seasons/{season_id}/ko-bracket/generate", response_model=schemas.KOBracket)
def generate_ko_bracket(season_id: int, db: Session = Depends(get_db), _: str = Depends(get_current_user)):
    """
    Generiert das komplette KO-Bracket und persistiert es.
    """
    existing = db.query(models.KOMatch).filter(models.KOMatch.season_id == season_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="KO bracket already exists for this season")

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
    total_rounds = bracket_size.bit_length() - 1

    bye_teams = team_ids[:byes_needed]
    playing_teams = team_ids[byes_needed:]

    all_matches = []

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

    db.flush()

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

    round1_matches = sorted(
        [m for m in all_matches if m.round == 1],
        key=lambda m: m.position
    )

    for i, team_id in enumerate(bye_teams):
        if i < len(round1_matches):
            match = round1_matches[i]
            match.home_team_id = team_id
            match.is_bye = 1
            match.status = "played"
            if match.next_match_id:
                next_match = db.get(models.KOMatch, match.next_match_id)
                if next_match:
                    if match.next_match_slot == "home":
                        next_match.home_team_id = team_id
                    else:
                        next_match.away_team_id = team_id

    match_idx = byes_needed
    for i in range(0, len(playing_teams), 2):
        if match_idx < len(round1_matches) and i + 1 < len(playing_teams):
            match = round1_matches[match_idx]
            match.home_team_id = playing_teams[i]
            match.away_team_id = playing_teams[i + 1]
            match.status = "scheduled"
            match_idx += 1

    db.commit()

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


@router.get("/ko-matches/batch")
def get_ko_matches_batch(match_ids: str, db: Session = Depends(get_db)):
    """
    Mehrere KO-Matches auf einmal abrufen für News-Embeddings.
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


# ============================================================
# KO-BRACKET ENDPOINTS (3-Bracket-System)
# ============================================================

@router.post("/seasons/{season_id}/ko-brackets/generate", status_code=201)
def generate_season_ko_brackets(
    season_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Generiert alle 3 KO-Brackets (Meister, Lucky Loser, Loser) für eine Saison (v2-Logik, keine Freilose)."""
    # Prüfe ob Season archiviert ist
    season = db.get(models.Season, season_id)
    if not season:
        raise HTTPException(status_code=404, detail="Saison nicht gefunden")
    if season.status == "archived":
        raise HTTPException(status_code=400, detail="KO-Logik v2 nicht für archivierte Saisons verfügbar")

    # Prüfe ob Brackets bereits existieren
    existing = db.query(models.KOBracket).filter(
        models.KOBracket.season_id == season_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="KO-Brackets bereits generiert für diese Saison"
        )

    try:
        result = generate_ko_brackets_v2(season_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return result


@router.get("/seasons/{season_id}/ko-brackets/preview")
def preview_season_ko_brackets(
    season_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Bracket-Vorschau ohne DB-Änderungen (für Admin-UI zum Überprüfen vor Generierung)."""
    season = db.get(models.Season, season_id)
    if not season:
        raise HTTPException(status_code=404, detail="Saison nicht gefunden")
    if season.status == "archived":
        raise HTTPException(status_code=400, detail="Archivierte Saison")

    try:
        return preview_ko_brackets(season_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/seasons/{season_id}/ko-brackets")
def get_season_ko_brackets(season_id: int, db: Session = Depends(get_db)):
    """Holt alle KO-Brackets einer Saison mit Matches."""
    brackets_data = {}

    for bracket_type in ["meister", "lucky_loser", "loser"]:
        bracket = db.query(models.KOBracket).filter(
            models.KOBracket.season_id == season_id,
            models.KOBracket.bracket_type == bracket_type
        ).first()

        if not bracket:
            brackets_data[bracket_type] = None
            continue

        matches = db.query(models.KOMatch).filter(
            models.KOMatch.season_id == season_id,
            models.KOMatch.bracket_type == bracket_type
        ).order_by(models.KOMatch.round, models.KOMatch.id).all()

        _ko_team_ids = set()
        for match in matches:
            if match.home_team_id: _ko_team_ids.add(match.home_team_id)
            if match.away_team_id: _ko_team_ids.add(match.away_team_id)
        _ko_teams_map = {t.id: t for t in db.query(models.Team).filter(models.Team.id.in_(_ko_team_ids)).all()} if _ko_team_ids else {}

        rounds_dict = {}
        for match in matches:
            round_key = f"runde_{match.round}"
            if round_key not in rounds_dict:
                rounds_dict[round_key] = []

            home_team = None
            away_team = None

            if match.home_team_id:
                home = _ko_teams_map.get(match.home_team_id)
                if home:
                    home_team = {"id": home.id, "name": home.name}

            if match.away_team_id:
                away = _ko_teams_map.get(match.away_team_id)
                if away:
                    away_team = {"id": away.id, "name": away.name}

            winner_id = None
            if match.home_goals is not None and match.away_goals is not None:
                if match.home_goals > match.away_goals:
                    winner_id = match.home_team_id
                elif match.away_goals > match.home_goals:
                    winner_id = match.away_team_id

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


@router.patch("/ko-matches/{match_id}")
def update_ko_match_result(
    match_id: int,
    update: schemas.KOMatchResultUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Trägt Ergebnis für ein KO-Match ein."""
    match = db.query(models.KOMatch).filter(
        models.KOMatch.id == match_id
    ).first()

    if not match:
        raise HTTPException(status_code=404, detail="KO-Match nicht gefunden")

    if match.is_bye == 1:
        raise HTTPException(status_code=400, detail="Freilos-Matches können nicht aktualisiert werden")

    home_goals = update.home_goals
    away_goals = update.away_goals
    winner_id = update.winner_id

    tiebreaker_used = False
    tiebreaker_reason = None
    tab_used = None

    if home_goals == away_goals:
        if winner_id is None:
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

    if home_goals != away_goals:
        winner_id = match.home_team_id if home_goals > away_goals else match.away_team_id

    if winner_id not in [match.home_team_id, match.away_team_id]:
        raise HTTPException(
            status_code=400,
            detail="winner_id muss einem der beiden Teams entsprechen"
        )

    match.home_goals = home_goals
    match.away_goals = away_goals
    match.status = "played"

    if match.next_match_id:
        next_match = db.get(models.KOMatch, match.next_match_id)
        if next_match:
            if match.next_match_slot == "home":
                next_match.home_team_id = winner_id
            else:
                next_match.away_team_id = winner_id

            if next_match.home_team_id and next_match.away_team_id:
                next_match.status = "scheduled"

    db.commit()

    bracket = db.query(models.KOBracket).filter(
        models.KOBracket.season_id == match.season_id,
        models.KOBracket.bracket_type == match.bracket_type
    ).first()

    if bracket:
        all_matches = db.query(models.KOMatch).filter(
            models.KOMatch.season_id == match.season_id,
            models.KOMatch.bracket_type == match.bracket_type
        ).all()

        if all(m.status == "played" for m in all_matches):
            bracket.status = "completed"
            db.commit()

    db.refresh(match)

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

    if tiebreaker_used:
        response["tiebreaker_used"] = True
        response["tiebreaker_reason"] = tiebreaker_reason
        response["tab_used"] = tab_used

    return response


@router.get("/seasons/{season_id}/ko-brackets/status")
def get_ko_brackets_status(season_id: int, db: Session = Depends(get_db)):
    """Schnelle Übersicht über KO-Bracket Status."""
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

    brackets = db.query(models.KOBracket).filter(
        models.KOBracket.season_id == season_id
    ).all()

    brackets_generated = len(brackets) > 0

    brackets_data = {}
    for bracket_type in ["meister", "lucky_loser", "loser"]:
        bracket = next((b for b in brackets if b.bracket_type == bracket_type), None)

        if not bracket:
            brackets_data[bracket_type] = None
            continue

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
    body: schemas.KOBracketCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Erstellt ein leeres KO-Bracket-Gerüst (ohne Team-Zuweisung)."""
    bracket_type = body.bracket_type
    team_count = body.team_count

    existing = db.query(models.KOBracket).filter(
        models.KOBracket.season_id == season_id,
        models.KOBracket.bracket_type == bracket_type
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Bracket '{bracket_type}' existiert bereits für diese Saison. Bitte zuerst zurücksetzen.")

    bracket = models.KOBracket(
        season_id=season_id,
        bracket_type=bracket_type,
        status="active",
        generated_at=datetime.utcnow()
    )
    db.add(bracket)
    db.flush()

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
    body: schemas.KOMatchSetTeam,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Setzt ein Team in einen Home- oder Away-Slot eines KO-Matches."""
    slot = body.slot
    team_id = body.team_id

    match = db.query(models.KOMatch).filter(models.KOMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="KO-Match nicht gefunden")

    if match.home_goals is not None:
        raise HTTPException(status_code=400, detail="Match bereits gespielt")

    if team_id is not None:
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
    body: schemas.KOMatchSetBye,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user)
):
    """Markiert ein KO-Match als Freilos und leitet Team in nächste Runde weiter."""
    team_id = body.team_id

    match = db.query(models.KOMatch).filter(models.KOMatch.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="KO-Match nicht gefunden")

    if match.home_goals is not None:
        raise HTTPException(status_code=400, detail="Match bereits gespielt")

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
