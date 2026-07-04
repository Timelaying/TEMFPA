"""Tests for Phase 6: FastAPI REST Layer."""

from __future__ import annotations

import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import temfpa.db.models  # noqa: F401 — must import to populate Base.metadata
from temfpa.db.base import Base
from temfpa.db.models import (
    Fixture,
    League,
    LeagueSeasonTeam,
    MatchResult,
    Season,
    Team,
)


# ---------------------------------------------------------------------------
# App factory with overridden DB dependency
# ---------------------------------------------------------------------------


def _make_test_app(db_session):
    """Create a fresh FastAPI app with the DB dependency overridden."""
    from temfpa.api.app import create_app
    from temfpa.api.dependencies import get_db

    app = create_app()

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db

    # Remove startup handler that would try to use the real engine
    app.router.on_startup.clear()

    return app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def db_engine():
    # StaticPool ensures a single shared connection across threads (required for
    # in-memory SQLite when endpoints run in a threadpool).
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def app(db):
    return _make_test_app(db)


# ---------------------------------------------------------------------------
# Helper: seed minimal data
# ---------------------------------------------------------------------------


def seed_minimal(db):
    """Seed a league, season, two teams, and some fixtures with results."""
    league = League(code="EPL", name="Premier League", country="England", tier=1)
    db.add(league)
    db.flush()

    season = Season(
        league_id=league.id,
        label="2023/2024",
        start_date=datetime.date(2023, 8, 1),
        end_date=datetime.date(2024, 5, 31),
    )
    db.add(season)
    db.flush()

    home = Team(name="Manchester City", short_name="Man City", country="England")
    away = Team(name="Liverpool", short_name="LFC", country="England")
    db.add_all([home, away])
    db.flush()

    # Link teams to league season
    db.add(LeagueSeasonTeam(league_id=league.id, season_id=season.id, team_id=home.id))
    db.add(LeagueSeasonTeam(league_id=league.id, season_id=season.id, team_id=away.id))
    db.flush()

    # Seed 3 finished fixtures
    for i, (hg, ag) in enumerate([(2, 0), (1, 1), (3, 1)]):
        dt = datetime.datetime(2023, 9, i + 1, 15, 0)
        f = Fixture(
            season_id=season.id,
            home_team_id=home.id,
            away_team_id=away.id,
            fixture_date=dt,
            status="FINISHED",
        )
        db.add(f)
        db.flush()
        winner = "draw" if hg == ag else ("home" if hg > ag else "away")
        db.add(MatchResult(fixture_id=f.id, home_goals=hg, away_goals=ag, winner=winner))
    db.commit()
    return league, season, home, away


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check(app):
    """GET /api/v2/health returns 200."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v2/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_get_leagues_empty(app):
    """GET /api/v2/leagues returns [] when no leagues."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v2/leagues")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_leagues_with_data(app, db):
    """Seed a league, assert it appears in /api/v2/leagues."""
    league = League(code="EPL", name="Premier League", country="England", tier=1)
    db.add(league)
    db.commit()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v2/leagues")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["code"] == "EPL"
    assert data[0]["name"] == "Premier League"


@pytest.mark.asyncio
async def test_get_teams_for_league(app, db):
    """Seed teams, GET /api/v2/teams/EPL returns them."""
    _, _, home, away = seed_minimal(db)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get("/api/v2/teams/EPL")
    assert resp.status_code == 200
    data = resp.json()
    names = {t["name"] for t in data}
    assert "Manchester City" in names
    assert "Liverpool" in names


@pytest.mark.asyncio
async def test_predict_returns_valid_response(app, db):
    """Seed minimal data, POST /api/v2/predict, assert valid PredictionResponse."""
    league, season, home, away = seed_minimal(db)

    payload = {
        "leagueId": "EPL",
        "season": "2023/2024",
        "homeTeamId": home.id,
        "awayTeamId": away.id,
        "fixtureDate": "2024-01-15",
        "includePlayerImpact": True,
        "includeFormationImpact": True,
        "includeScorePrediction": True,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v2/predict", json=payload)

    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Validate required top-level keys
    assert "fixture" in data
    assert "prediction" in data
    assert "topScorelines" in data
    assert "keyFactors" in data
    assert "teamComparison" in data

    # Validate prediction structure
    pred = data["prediction"]
    assert "result" in pred
    assert "confidence" in pred
    assert "homeWinProbability" in pred
    assert "drawProbability" in pred
    assert "awayWinProbability" in pred
    assert "likelyScore" in pred


@pytest.mark.asyncio
async def test_predict_missing_team_returns_404(app, db):
    """POST with invalid homeTeamId returns 404."""
    league = League(code="TST", name="Test League", country="England", tier=1)
    db.add(league)
    db.flush()
    season = Season(
        league_id=league.id,
        label="2023/2024",
        start_date=datetime.date(2023, 8, 1),
        end_date=datetime.date(2024, 5, 31),
    )
    db.add(season)
    db.commit()

    payload = {
        "leagueId": "TST",
        "season": "2023/2024",
        "homeTeamId": 99999,
        "awayTeamId": 99998,
        "fixtureDate": "2024-01-15",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v2/predict", json=payload)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_predict_response_probabilities_sum_to_one(app, db):
    """Assert home+draw+away probabilities sum to approximately 1.0."""
    league, season, home, away = seed_minimal(db)

    payload = {
        "leagueId": "EPL",
        "season": "2023/2024",
        "homeTeamId": home.id,
        "awayTeamId": away.id,
        "fixtureDate": "2024-01-15",
        "includePlayerImpact": False,
        "includeFormationImpact": False,
        "includeScorePrediction": True,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post("/api/v2/predict", json=payload)

    assert resp.status_code == 200, resp.text
    pred = resp.json()["prediction"]
    total = pred["homeWinProbability"] + pred["drawProbability"] + pred["awayWinProbability"]
    assert abs(total - 1.0) < 0.05  # Allow small rounding


@pytest.mark.asyncio
async def test_get_fixtures(app, db):
    """Seed fixtures, GET /api/v2/fixtures?leagueId=EPL&season=2023/2024."""
    seed_minimal(db)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/v2/fixtures",
            params={"leagueId": "EPL", "season": "2023/2024"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3  # 3 seeded fixtures
    for f in data:
        assert "homeTeam" in f
        assert "awayTeam" in f
        assert "date" in f
