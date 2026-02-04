from pydantic import BaseModel
from datetime import datetime


# Auth Schemas
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str

class SeasonCreate(BaseModel):
    name: str
    participant_count: int


class SeasonUpdate(BaseModel):
    name: str | None = None
    status: str | None = None


class SeasonRead(BaseModel):
    id: int
    name: str
    participant_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class GroupRead(BaseModel):
    id: int
    season_id: int
    name: str
    sort_order: int

    class Config:
        from_attributes = True

class TeamCreate(BaseModel):
    name: str
    logo_url: str | None = None
    onlineliga_url: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = None
    logo_url: str | None = None
    onlineliga_url: str | None = None


class BulkTeamCreate(BaseModel):
    teams: list[str]


class TeamRead(BaseModel):
    id: int
    name: str
    logo_url: str | None = None
    onlineliga_url: str | None = None

    class Config:
        from_attributes = True


class TeamDetailMatch(BaseModel):
    """Match-Info für Team-Profil"""
    id: int
    season_name: str
    opponent_id: int
    opponent_name: str
    is_home: bool
    own_goals: int | None
    opponent_goals: int | None
    result: str  # "win", "draw", "loss", "scheduled"
    date: datetime | None


class TeamDetail(BaseModel):
    """Vollständige Team-Info mit letzten Spielen"""
    id: int
    name: str
    logo_url: str | None
    onlineliga_url: str | None
    recent_matches: list[TeamDetailMatch]
    stats: dict  # Gesamt-Statistiken

    class Config:
        from_attributes = True

class MatchCreate(BaseModel):
    home_team_id: int
    away_team_id: int

class MatchRead(BaseModel):
    id: int
    home_team_id: int
    away_team_id: int
    home_goals: int | None
    away_goals: int | None
    status: str

    class Config:
        from_attributes = True


class KORound(BaseModel):
    name: str
    teams: list[int]
    byes: list[int]


class KOPlan(BaseModel):
    season_id: int
    qualified_team_ids: list[int]
    rounds: list[KORound]


class MatchUpdate(BaseModel):
    home_goals: int | None = None
    away_goals: int | None = None
    status: str | None = None
    ingame_week: int | None = None


# KO-Phase Schemas
class KOMatchRead(BaseModel):
    id: int
    season_id: int
    round: int
    position: int
    home_team_id: int | None
    away_team_id: int | None
    home_goals: int | None
    away_goals: int | None
    is_bye: int
    status: str
    next_match_id: int | None
    next_match_slot: str | None

    class Config:
        from_attributes = True


class KOMatchUpdate(BaseModel):
    home_goals: int | None = None
    away_goals: int | None = None
    status: str | None = None
    ingame_week: int | None = None


class KOBracket(BaseModel):
    season_id: int
    total_rounds: int
    matches: list[KOMatchRead]


# News Schemas
class NewsCreate(BaseModel):
    title: str
    content: str
    author: str | None = "Admin"
    published: int | None = 1


class NewsUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    author: str | None = None
    published: int | None = None


class NewsRead(BaseModel):
    id: int
    title: str
    content: str
    author: str
    published: int
    created_at: datetime

    class Config:
        from_attributes = True
