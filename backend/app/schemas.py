from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional


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
    group_id: int | None = None  # Optional: explizite Gruppenzuweisung für Import


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
    home_goals: int | None = None
    away_goals: int | None = None
    status: str | None = None
    matchday: int | None = None
    ingame_week: int | None = None

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
    home_team_id: int | None = None
    away_team_id: int | None = None
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


# ============================================================
# Discord Bot & User Profile Schemas
# ============================================================

class UserProfileBase(BaseModel):
    """Basis-Schema für UserProfile"""
    discord_id: str
    discord_username: Optional[str] = None
    profile_url: Optional[HttpUrl] = None
    participating_next: bool = True


class UserProfileCreate(UserProfileBase):
    """Schema für User-Registrierung (Admin-Only)"""
    team_id: Optional[int] = None


class UserProfileUpdate(BaseModel):
    """Schema für User-Updates (partielle Updates)"""
    profile_url: Optional[HttpUrl] = None
    participating_next: Optional[bool] = None
    team_id: Optional[int] = None


class UserProfileAdminUpdate(BaseModel):
    """Schema für Admin-Update eines User Profiles"""
    discord_username: Optional[str] = None
    team_id: Optional[int] = None
    profile_url: Optional[str] = None
    participating_next: Optional[bool] = None
    crest_url: Optional[str] = None


class UserProfileResponse(BaseModel):
    """Response-Schema mit verknüpften Team-Daten"""
    id: int
    discord_id: str
    discord_username: Optional[str] = None
    discord_avatar_url: Optional[str] = None
    team_id: Optional[int] = None
    team_name: Optional[str] = None  # Joined aus Team
    profile_url: Optional[str] = None
    participating_next: bool
    crest_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ParticipationUpdate(BaseModel):
    """Schema für Teilnahme-Update via Discord Bot"""
    participating: bool = Field(..., description="Teilnahme am nächsten Pokal")


class ProfileUrlUpdate(BaseModel):
    """Schema für Profil-URL Update via Discord Bot"""
    profile_url: HttpUrl = Field(..., description="Onlineliga Profil-URL")


class ParticipationReport(BaseModel):
    """Admin-Report über Teilnahme-Status"""
    total_users: int
    participating: int
    not_participating: int
    participation_rate: float  # Prozent
    users: list[UserProfileResponse]


# ============================================================
# OAuth2 & Auth Schemas
# ============================================================

class DiscordUserInfo(BaseModel):
    """Discord User-Info vom OAuth2 Callback"""
    id: str
    username: str
    discriminator: str
    avatar: Optional[str] = None
    email: Optional[str] = None


class OAuth2CallbackResponse(BaseModel):
    """Response nach erfolgreichem OAuth2 Login"""
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse


class MeResponse(BaseModel):
    """Response für /api/auth/me Endpoint"""
    discord_id: str
    discord_username: str
    team_name: Optional[str] = None
    authenticated: bool = True


# ============================================================
# File Upload Schemas
# ============================================================

class CrestUploadResponse(BaseModel):
    """Response nach erfolgreichem Wappen-Upload"""
    crest_url: str
    message: str = "Wappen erfolgreich hochgeladen"


class CrestDeleteResponse(BaseModel):
    """Response nach Wappen-Löschung"""
    message: str = "Wappen erfolgreich gelöscht"
