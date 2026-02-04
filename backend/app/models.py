from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from .db import Base

class Season(Base):
    __tablename__ = "seasons"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    participant_count = Column(Integer, nullable=False)
    status = Column(String, default="planned")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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


class KOMatch(Base):
    """
    KO-Phase Match mit Bracket-Struktur.
    round: 1=Erste Runde, 2=Viertelfinale, 3=Halbfinale, 4=Finale (je nach Bracket-Größe)
    position: Position im Bracket (1-basiert, von oben nach unten)
    next_match_id: Verweis auf das Folge-Match (Sieger spielt dort)
    """
    __tablename__ = "ko_matches"
    id = Column(Integer, primary_key=True, index=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
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