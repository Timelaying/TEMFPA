"""SQLAlchemy ORM models for TEMFPA V.2.

All tables use integer surrogate primary keys. External provider IDs are stored
in JSON columns so the same row can be enriched from multiple sources without
re-keying.
"""

from __future__ import annotations

import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from temfpa.db.base import Base


# ---------------------------------------------------------------------------
# Reference / dimension tables
# ---------------------------------------------------------------------------


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(60), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # e.g. {"api_football": 39, "football_data": "PL", "fbref": "ENG-Premier League"}
    provider_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    seasons: Mapped[list[Season]] = relationship("Season", back_populates="league")
    league_season_teams: Mapped[list[LeagueSeasonTeam]] = relationship(
        "LeagueSeasonTeam", back_populates="league"
    )

    def __repr__(self) -> str:
        return f"<League {self.code}>"


class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = (UniqueConstraint("league_id", "label"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(20), nullable=False)  # "2023/2024"
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)

    league: Mapped[League] = relationship("League", back_populates="seasons")
    fixtures: Mapped[list[Fixture]] = relationship("Fixture", back_populates="season")
    league_season_teams: Mapped[list[LeagueSeasonTeam]] = relationship(
        "LeagueSeasonTeam", back_populates="season"
    )

    def __repr__(self) -> str:
        return f"<Season {self.label}>"


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    country: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # e.g. {"api_football": 33, "football_data": 57, "fbref": "Manchester City"}
    provider_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    players: Mapped[list[Player]] = relationship("Player", back_populates="team")
    coaches: Mapped[list[Coach]] = relationship("Coach", back_populates="team")
    home_fixtures: Mapped[list[Fixture]] = relationship(
        "Fixture", foreign_keys="Fixture.home_team_id", back_populates="home_team"
    )
    away_fixtures: Mapped[list[Fixture]] = relationship(
        "Fixture", foreign_keys="Fixture.away_team_id", back_populates="away_team"
    )
    league_season_teams: Mapped[list[LeagueSeasonTeam]] = relationship(
        "LeagueSeasonTeam", back_populates="team"
    )

    def __repr__(self) -> str:
        return f"<Team {self.name}>"


class LeagueSeasonTeam(Base):
    """Junction table: which teams compete in each league season."""

    __tablename__ = "league_season_teams"
    __table_args__ = (UniqueConstraint("league_id", "season_id", "team_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)

    league: Mapped[League] = relationship("League", back_populates="league_season_teams")
    season: Mapped[Season] = relationship("Season", back_populates="league_season_teams")
    team: Mapped[Team] = relationship("Team", back_populates="league_season_teams")


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str | None] = mapped_column(String(10), nullable=True)  # GK/DEF/MID/FWD
    nationality: Mapped[str | None] = mapped_column(String(60), nullable=True)
    dob: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    provider_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    team: Mapped[Team | None] = relationship("Team", back_populates="players")
    lineup_entries: Mapped[list[LineupPlayer]] = relationship(
        "LineupPlayer", back_populates="player"
    )
    match_stats: Mapped[list[PlayerMatchStat]] = relationship(
        "PlayerMatchStat", back_populates="player"
    )
    absences: Mapped[list[InjuryOrAbsence]] = relationship(
        "InjuryOrAbsence", back_populates="player"
    )

    def __repr__(self) -> str:
        return f"<Player {self.name}>"


class Coach(Base):
    __tablename__ = "coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    nationality: Mapped[str | None] = mapped_column(String(60), nullable=True)
    appointed: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    provider_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    team: Mapped[Team | None] = relationship("Team", back_populates="coaches")

    def __repr__(self) -> str:
        return f"<Coach {self.name}>"


# ---------------------------------------------------------------------------
# Match data tables
# ---------------------------------------------------------------------------


class Fixture(Base):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    fixture_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    venue: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # SCHEDULED | LIVE | FINISHED | POSTPONED | CANCELLED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="SCHEDULED")
    matchweek: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_ids: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    season: Mapped[Season] = relationship("Season", back_populates="fixtures")
    home_team: Mapped[Team] = relationship(
        "Team", foreign_keys=[home_team_id], back_populates="home_fixtures"
    )
    away_team: Mapped[Team] = relationship(
        "Team", foreign_keys=[away_team_id], back_populates="away_fixtures"
    )
    result: Mapped[MatchResult | None] = relationship(
        "MatchResult", back_populates="fixture", uselist=False
    )
    lineups: Mapped[list[Lineup]] = relationship("Lineup", back_populates="fixture")
    player_stats: Mapped[list[PlayerMatchStat]] = relationship(
        "PlayerMatchStat", back_populates="fixture"
    )
    team_stats: Mapped[list[TeamMatchStat]] = relationship(
        "TeamMatchStat", back_populates="fixture"
    )
    predictions: Mapped[list[Prediction]] = relationship(
        "Prediction", back_populates="fixture"
    )

    def __repr__(self) -> str:
        return f"<Fixture {self.id}: {self.home_team_id} vs {self.away_team_id}>"


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(
        ForeignKey("fixtures.id"), nullable=False, unique=True
    )
    home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    home_ht_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_ht_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # "home" | "away" | "draw"
    winner: Mapped[str | None] = mapped_column(String(10), nullable=True)
    home_xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    fixture: Mapped[Fixture] = relationship("Fixture", back_populates="result")

    def __repr__(self) -> str:
        return f"<MatchResult fixture={self.fixture_id} {self.home_goals}-{self.away_goals}>"


class Lineup(Base):
    __tablename__ = "lineups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    formation: Mapped[str | None] = mapped_column(String(20), nullable=True)  # "4-3-3"
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    fixture: Mapped[Fixture] = relationship("Fixture", back_populates="lineups")
    players: Mapped[list[LineupPlayer]] = relationship(
        "LineupPlayer", back_populates="lineup"
    )

    def __repr__(self) -> str:
        return f"<Lineup fixture={self.fixture_id} team={self.team_id} {self.formation}>"


class LineupPlayer(Base):
    __tablename__ = "lineup_players"
    __table_args__ = (UniqueConstraint("lineup_id", "player_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lineup_id: Mapped[int] = mapped_column(ForeignKey("lineups.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    shirt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_starter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    lineup: Mapped[Lineup] = relationship("Lineup", back_populates="players")
    player: Mapped[Player] = relationship("Player", back_populates="lineup_entries")


class InjuryOrAbsence(Base):
    __tablename__ = "injuries_or_absences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    # NULL means ongoing absence (not tied to a specific fixture)
    fixture_id: Mapped[int | None] = mapped_column(
        ForeignKey("fixtures.id"), nullable=True
    )
    # "injury" | "suspension" | "international_duty" | "unknown"
    reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    start_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    player: Mapped[Player] = relationship("Player", back_populates="absences")


# ---------------------------------------------------------------------------
# Per-match statistics
# ---------------------------------------------------------------------------


class PlayerMatchStat(Base):
    __tablename__ = "player_match_stats"
    __table_args__ = (UniqueConstraint("fixture_id", "player_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    minutes_played: Mapped[int | None] = mapped_column(Integer, nullable=True)
    goals: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assists: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    yellow_cards: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    red_cards: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    xa: Mapped[float | None] = mapped_column(Float, nullable=True)

    fixture: Mapped[Fixture] = relationship("Fixture", back_populates="player_stats")
    player: Mapped[Player] = relationship("Player", back_populates="match_stats")


class TeamMatchStat(Base):
    __tablename__ = "team_match_stats"
    __table_args__ = (UniqueConstraint("fixture_id", "team_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    formation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    possession: Mapped[float | None] = mapped_column(Float, nullable=True)
    shots: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shots_on_target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    corners: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fouls: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    ppda: Mapped[float | None] = mapped_column(Float, nullable=True)

    fixture: Mapped[Fixture] = relationship("Fixture", back_populates="team_stats")


# ---------------------------------------------------------------------------
# Prediction output tables
# ---------------------------------------------------------------------------


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (UniqueConstraint("request_hash", "model_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int | None] = mapped_column(
        ForeignKey("fixtures.id"), nullable=True
    )
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(20), nullable=False)
    # "home" | "away" | "draw"
    result: Mapped[str | None] = mapped_column(String(10), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(10), nullable=True)  # High/Medium/Low
    home_win_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    draw_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_win_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_home_goals: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_away_goals: Mapped[float | None] = mapped_column(Float, nullable=True)
    likely_score: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    fixture: Mapped[Fixture | None] = relationship("Fixture", back_populates="predictions")
    scorelines: Mapped[list[PredictionScoreline]] = relationship(
        "PredictionScoreline", back_populates="prediction"
    )
    explanation: Mapped[PredictionExplanation | None] = relationship(
        "PredictionExplanation", back_populates="prediction", uselist=False
    )

    def __repr__(self) -> str:
        return f"<Prediction {self.id}: {self.result} ({self.confidence})>"


class PredictionScoreline(Base):
    __tablename__ = "prediction_scorelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("predictions.id"), nullable=False
    )
    home_goals: Mapped[int] = mapped_column(Integer, nullable=False)
    away_goals: Mapped[int] = mapped_column(Integer, nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3

    prediction: Mapped[Prediction] = relationship(
        "Prediction", back_populates="scorelines"
    )


class PredictionExplanation(Base):
    __tablename__ = "prediction_explanations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("predictions.id"), nullable=False, unique=True
    )
    # JSON list of {factor, description, impact, direction}
    key_factors: Mapped[list] = mapped_column(JSON, nullable=False)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)

    prediction: Mapped[Prediction] = relationship(
        "Prediction", back_populates="explanation"
    )


class PredictionLog(Base):
    """One row per prediction shown to the user — tracked for accuracy comparison."""

    __tablename__ = "prediction_logs"
    __table_args__ = (
        # Prevent duplicate entries for the same matchup from the same source.
        # fixture_id can be NULL for showcase matchups, so key on team IDs + date.
        UniqueConstraint("home_team_id", "away_team_id", "fixture_date", "source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Fixture FK — NULL for showcase matchups not yet in the fixtures table
    fixture_id: Mapped[int | None] = mapped_column(
        ForeignKey("fixtures.id"), nullable=True, index=True
    )

    # Denormalised for convenience
    league_code: Mapped[str] = mapped_column(String(20), nullable=False)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    fixture_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)

    # Prediction at log time
    predicted_result: Mapped[str] = mapped_column(String(10), nullable=False)     # home/draw/away
    predicted_confidence: Mapped[str] = mapped_column(String(10), nullable=False)  # High/Medium/Low
    home_win_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    draw_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_win_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    likely_score: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # "upcoming" (auto-generated) | "manual" (user submitted)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="upcoming")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Filled in after the match result is known
    actual_result: Mapped[str | None] = mapped_column(String(10), nullable=True)
    actual_home_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actual_away_goals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
