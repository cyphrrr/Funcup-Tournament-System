from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .db import Base

class Season(Base):
    __tablename__ = "seasons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    participant_count = Column(Integer, nullable=False)
    status = Column(String, default="planned")
    sheet_tab_gid = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    ko_brackets = relationship("KOBracket", back_populates="season", cascade="all, delete-orphan")

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)  # Wappen/Logo
    onlineliga_url = Column(String, nullable=True)  # Link zu onlineliga.de
    participating_next = Column(Boolean, default=False)  # Dabei am nächsten Pokal (Team-Level)
    is_active = Column(Boolean, default=True, nullable=False)  # Soft-Delete

class SeasonTeam(Base):
    __tablename__ = "season_teams"
    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=True)

class Match(Base):
    __tablename__ = "matches"
    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)
    status = Column(String, default="scheduled")
    matchday = Column(Integer, nullable=True)  # Spieltag-Nummer (1, 2, 3, ...)
    ingame_week = Column(Integer, nullable=True)  # Ingame Spielwoche (z.B. W39)


class News(Base):
    """News/Blog-Artikel für die Turnierseite."""
    __tablename__ = "news"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    author = Column(String, default="Admin")
    published = Column(Integer, default=1)  # 1 = veröffentlicht, 0 = Entwurf
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class KOBracket(Base):
    """
    KO-Bracket für 3-Bracket-System.
    Pro Saison gibt es 3 Brackets: Meister, Lucky Loser, Loser.
    """
    __tablename__ = "ko_brackets"
    __table_args__ = (
        UniqueConstraint('season_id', 'bracket_type', name='uix_season_bracket'),
    )

    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    bracket_type = Column(String, nullable=False)  # "meister" | "lucky_loser" | "loser"
    status = Column(String, nullable=False, default="pending")  # "pending" | "active" | "completed"
    generated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    season = relationship("Season", back_populates="ko_brackets")
    matches = relationship(
        "KOMatch",
        back_populates="bracket",
        primaryjoin="and_(KOBracket.season_id==KOMatch.season_id, KOBracket.bracket_type==KOMatch.bracket_type)",
        foreign_keys="[KOMatch.season_id, KOMatch.bracket_type]",
        cascade="all, delete-orphan"
    )


class KOMatch(Base):
    """
    KO-Phase Match mit Bracket-Struktur.
    round: 1=Erste Runde, 2=Viertelfinale, 3=Halbfinale, 4=Finale (je nach Bracket-Größe)
    position: Position im Bracket (1-basiert, von oben nach unten)
    next_match_id: Verweis auf das Folge-Match (Sieger spielt dort)
    bracket_type: Zugehörigkeit zu einem der 3 Brackets (meister/lucky_loser/loser)
    """
    __tablename__ = "ko_matches"
    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    bracket_type = Column(String, nullable=False)  # "meister" | "lucky_loser" | "loser"
    round = Column(Integer, nullable=False)  # Rundennummer
    position = Column(Integer, nullable=False)  # Position in der Runde
    home_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)  # nullable für Freilose/TBD
    away_team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    home_goals = Column(Integer, nullable=True)
    away_goals = Column(Integer, nullable=True)
    is_bye = Column(Integer, default=0)  # 1 = Freilos (Team steigt direkt auf)
    status = Column(String, default="pending")  # pending, scheduled, played
    ingame_week = Column(Integer, nullable=True)  # Ingame Spielwoche (z.B. W39)
    next_match_id = Column(Integer, ForeignKey("ko_matches.id"), nullable=True)
    next_match_slot = Column(String, nullable=True)  # "home" oder "away" - wohin der Sieger geht
    is_third_place = Column(Integer, default=0)  # 1 = Spiel um Platz 3
    loser_next_match_id = Column(Integer, ForeignKey("ko_matches.id"), nullable=True)
    loser_next_match_slot = Column(String, nullable=True)  # "home" | "away"

    # Relationship zu KOBracket
    bracket = relationship(
        "KOBracket",
        back_populates="matches",
        primaryjoin="and_(KOMatch.season_id==KOBracket.season_id, KOMatch.bracket_type==KOBracket.bracket_type)",
        foreign_keys="[KOMatch.season_id, KOMatch.bracket_type]",
        viewonly=True
    )


class UserProfile(Base):
    """
    User Profile für Discord-Integration.
    Verknüpft Discord-User mit Teams und speichert OAuth2-Daten.
    """
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)

    # Discord-Daten
    discord_id = Column(String, unique=True, index=True, nullable=True)  # Discord Snowflake ID
    discord_username = Column(String, nullable=True)  # z.B. "Max#1234"
    discord_avatar_url = Column(String, nullable=True)  # Discord Avatar URL

    # Team-Verknüpfung
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)  # Verknüpftes Team

    # User-Daten
    profile_url = Column(String, nullable=True)  # Onlineliga Profil-URL
    crest_url = Column(String, nullable=True)  # Custom Wappen-URL (uploads/)
    is_active = Column(Boolean, default=True, nullable=False)  # Soft-Delete

    # OAuth2 Token Storage (für Discord OAuth2)
    # WICHTIG: In Production mit Encryption speichern!
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship zu Team (optional)
    team = relationship("Team", backref="user_profile", foreign_keys=[team_id])


class Background(Base):
    """Hintergrundbilder für öffentliche Seiten."""
    __tablename__ = "backgrounds"
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False, unique=True)
    original_name = Column(String, nullable=False)
    is_active = Column(Integer, default=0)
    opacity = Column(Integer, default=15)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())


class PageView(Base):
    __tablename__ = "page_views"
    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, nullable=False)
    visitor_id = Column(String, nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    referrer = Column(String, nullable=True)