"""Shared test fixtures for TEMFPA V.2 tests."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from temfpa.db.base import Base
from temfpa.db.models import (
    Coach,
    Fixture,
    League,
    LeagueSeasonTeam,
    Lineup,
    LineupPlayer,
    MatchResult,
    Player,
    PlayerMatchStat,
    Prediction,
    PredictionExplanation,
    PredictionScoreline,
    Season,
    Team,
    TeamMatchStat,
)


@pytest.fixture(scope="function")
def db_engine():
    """In-memory SQLite engine with all tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Database session for a single test."""
    TestSession = sessionmaker(bind=db_engine)
    session = TestSession()
    yield session
    session.rollback()
    session.close()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def sample_league(db_session: Session) -> League:
    league = League(
        code="EPL",
        name="English Premier League",
        country="England",
        tier=1,
        provider_ids={"fbref": "ENG-Premier League"},
    )
    db_session.add(league)
    db_session.commit()
    return league


@pytest.fixture(scope="function")
def sample_season(db_session: Session, sample_league: League) -> Season:
    season = Season(
        league_id=sample_league.id,
        label="2023/2024",
        start_date=datetime.date(2023, 8, 11),
        end_date=datetime.date(2024, 5, 19),
    )
    db_session.add(season)
    db_session.commit()
    return season


@pytest.fixture(scope="function")
def sample_teams(db_session: Session) -> tuple[Team, Team]:
    home = Team(name="Manchester City", short_name="Man City", country="England")
    away = Team(name="Liverpool", short_name="LFC", country="England")
    db_session.add_all([home, away])
    db_session.commit()
    return home, away


@pytest.fixture(scope="function")
def sample_fixture(
    db_session: Session,
    sample_season: Season,
    sample_teams: tuple[Team, Team],
) -> Fixture:
    home, away = sample_teams
    fixture = Fixture(
        season_id=sample_season.id,
        home_team_id=home.id,
        away_team_id=away.id,
        fixture_date=datetime.datetime(2023, 11, 25, 12, 30),
        venue="Etihad Stadium",
        status="FINISHED",
        matchweek=13,
    )
    db_session.add(fixture)
    db_session.commit()
    return fixture
