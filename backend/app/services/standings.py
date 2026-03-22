from urllib.parse import unquote
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models, ranking_service
from ..db import get_db

router = APIRouter()


@router.get("/all-time-standings")
def get_all_time_standings(db: Session = Depends(get_db)):
    """
    Ewige Tabelle: Aggregierte Statistiken aller Teams über alle Saisons.
    Berücksichtigt sowohl Gruppenphase als auch KO-Phase Spiele.
    """
    all_matches = db.query(models.Match).filter(models.Match.status == "played").all()
    all_ko = db.query(models.KOMatch).filter(
        models.KOMatch.status == "played",
        models.KOMatch.is_bye == 0
    ).all()

    teams = {t.id: t.name for t in db.query(models.Team).all()}

    team_stats = {}

    def ensure_stats(team_id):
        name = teams.get(team_id, "?")
        if name not in team_stats:
            team_stats[name] = {
                "team_id": team_id,
                "team_name": name,
                "played": 0, "won": 0, "draw": 0, "lost": 0,
                "goals_for": 0, "goals_against": 0, "points": 0
            }
        return team_stats[name]

    for m in all_matches:
        if m.home_goals is None or m.away_goals is None:
            continue
        s = ensure_stats(m.home_team_id)
        s["played"] += 1
        s["goals_for"] += m.home_goals
        s["goals_against"] += m.away_goals
        if m.home_goals > m.away_goals:
            s["won"] += 1; s["points"] += 3
        elif m.home_goals == m.away_goals:
            s["draw"] += 1; s["points"] += 1
        else:
            s["lost"] += 1

        s = ensure_stats(m.away_team_id)
        s["played"] += 1
        s["goals_for"] += m.away_goals
        s["goals_against"] += m.home_goals
        if m.away_goals > m.home_goals:
            s["won"] += 1; s["points"] += 3
        elif m.away_goals == m.home_goals:
            s["draw"] += 1; s["points"] += 1
        else:
            s["lost"] += 1

    for m in all_ko:
        if m.home_goals is None or m.away_goals is None:
            continue
        s = ensure_stats(m.home_team_id)
        s["played"] += 1
        s["goals_for"] += m.home_goals
        s["goals_against"] += m.away_goals
        if m.home_goals > m.away_goals:
            s["won"] += 1; s["points"] += 3
        else:
            s["lost"] += 1

        s = ensure_stats(m.away_team_id)
        s["played"] += 1
        s["goals_for"] += m.away_goals
        s["goals_against"] += m.home_goals
        if m.away_goals > m.home_goals:
            s["won"] += 1; s["points"] += 3
        else:
            s["lost"] += 1

    standings = [s for s in team_stats.values() if s["played"] > 0]
    standings.sort(
        key=lambda x: (x["points"], x["goals_for"] - x["goals_against"], x["goals_for"]),
        reverse=True
    )
    return standings


@router.get("/ranking/team/{team_name}")
def get_team_ranking_endpoint(team_name: str, db: Session = Depends(get_db)):
    """Public Endpoint: Holt Ranking-Details eines Teams."""
    team_name = unquote(team_name)
    details = ranking_service.get_team_ranking_details(team_name, db)
    return details


@router.get("/ranking/all")
def get_all_rankings(db: Session = Depends(get_db)):
    """Public Endpoint: Gibt komplettes Ranking-Sheet zurück."""
    teams = ranking_service.fetch_ranking_sheet(db)

    return {
        "tab_used": "Erster Tab (aktuelles Ranking)",
        "teams": teams
    }
