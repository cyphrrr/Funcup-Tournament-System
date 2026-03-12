from pydantic import BaseModel, HttpUrl, Field, validator
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
    group_count: Optional[int] = None  # Optional: Admin bestimmt Gruppenanzahl manuell


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
    discord_claimed: bool  # Ob das Team via Discord geclaimt wurde
    recent_matches: list[TeamDetailMatch]
    stats: dict  # Gesamt-Statistiken

    class Config:
        from_attributes = True

class SyncTeamsPayload(BaseModel):
    team_ids: list[int]
    seeded_teams: dict[str, int] = {}  # {"A": team_id, "B": team_id, "C": team_id}
    generate_schedule: bool = True


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
    is_third_place: int = 0
    loser_next_match_id: Optional[int] = None
    loser_next_match_slot: Optional[str] = None

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
    discord_id: Optional[str] = None
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
    discord_id: Optional[str] = None
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


class TeamClaimRequest(BaseModel):
    """Request für Team-Claim via Discord Bot"""
    team_id: int


class UserEnsureRequest(BaseModel):
    """Request schema for ensure user endpoint (Upsert)."""
    discord_id: str = Field(..., description="Discord User ID (Snowflake)")
    discord_username: Optional[str] = Field(None, description="Discord username")
    discord_avatar_url: Optional[str] = Field(None, description="Discord avatar URL")


class AdminSetTeamRequest(BaseModel):
    """Admin-Request: Team für User setzen/entfernen"""
    team_id: Optional[int] = Field(None, description="Team ID oder null zum Entfernen")


class UserDeleteResponse(BaseModel):
    """Response nach User-Löschung"""
    deleted: bool = True
    discord_id: str


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


# ============================================================
# KO-Match Typed Request Schemas
# ============================================================

class KOMatchResultUpdate(BaseModel):
    """Body für PATCH /ko-matches/{id} (Ergebnis eintragen)"""
    home_goals: int = Field(..., ge=0)
    away_goals: int = Field(..., ge=0)
    winner_id: Optional[int] = None


class KOBracketCreate(BaseModel):
    """Body für POST /seasons/{id}/ko-brackets/create-empty"""
    bracket_type: str = Field(..., pattern="^(meister|lucky_loser|loser)$")
    team_count: int

    @validator('team_count')
    def valid_team_count(cls, v):
        if v not in [2, 4, 8, 16, 32]:
            raise ValueError('team_count muss 2, 4, 8, 16 oder 32 sein')
        return v


class KOMatchSetTeam(BaseModel):
    """Body für PATCH /ko-matches/{id}/set-team"""
    slot: str = Field(..., pattern="^(home|away)$")
    team_id: Optional[int] = None


class KOMatchSetBye(BaseModel):
    """Body für PATCH /ko-matches/{id}/set-bye"""
    team_id: int


# ============================================================
# Match Bulk Update Schemas
# ============================================================

class MatchBulkUpdateItem(BaseModel):
    match_id: int
    home_goals: int
    away_goals: int
    ingame_week: Optional[int] = None

class MatchBulkUpdateRequest(BaseModel):
    matches: list[MatchBulkUpdateItem]

class MatchBulkUpdateResponse(BaseModel):
    updated: int
    errors: list[str]


# ============================================================
# Match Import Schemas (n8n)
# ============================================================

class MatchImportItem(BaseModel):
    """Ein Ergebnis aus dem n8n-Import"""
    Heim: str
    Gast: str
    Heimtore: str
    Gasttore: str
    Saison: str
    Spieltag: str


class MatchImportError(BaseModel):
    heim: str
    gast: str
    reason: str


class MatchImportResponse(BaseModel):
    imported: int
    skipped: int
    swapped: int
    errors: list[MatchImportError]
