"""Tests for the ingestion layer using fakes — no real network calls."""

from __future__ import annotations

import datetime

import pytest

from temfpa.ingestion.base import (
    FixtureDTO,
    MatchResultDTO,
    LineupDTO,
    PlayerMatchStatDTO,
    ProviderError,
    TeamMatchStatDTO,
)
from temfpa.ingestion.router import IngestionRouter
from temfpa.ingestion.sync import (
    _get_or_create_league,
    _get_or_create_season,
    _get_or_create_team,
    _normalise_team_name,
    sync_fixtures,
    sync_results,
)


# ---------------------------------------------------------------------------
# Fake providers
# ---------------------------------------------------------------------------

SAMPLE_DATE = datetime.datetime(2023, 11, 25, 12, 30)


class AlwaysFailProvider:
    name = "fail"

    def is_available(self) -> bool:
        return True

    def fetch_results(self, *a, **kw):
        raise ProviderError("intentional failure")

    def fetch_fixtures(self, *a, **kw):
        raise ProviderError("intentional failure")

    def fetch_lineups(self, *a, **kw):
        return []

    def fetch_player_stats(self, *a, **kw):
        return []

    def fetch_team_stats(self, *a, **kw):
        return []


class UnavailableProvider:
    name = "unavailable"

    def is_available(self) -> bool:
        return False

    def fetch_results(self, *a, **kw):
        raise AssertionError("should not be called")

    def fetch_fixtures(self, *a, **kw):
        raise AssertionError("should not be called")

    def fetch_lineups(self, *a, **kw):
        raise AssertionError("should not be called")

    def fetch_player_stats(self, *a, **kw):
        raise AssertionError("should not be called")

    def fetch_team_stats(self, *a, **kw):
        raise AssertionError("should not be called")


class FakeProvider:
    name = "fake"

    def __init__(self, results=None, fixtures=None, lineups=None, player_stats=None, team_stats=None):
        self._results = results or []
        self._fixtures = fixtures or []
        self._lineups = lineups or []
        self._player_stats = player_stats or []
        self._team_stats = team_stats or []

    def is_available(self) -> bool:
        return True

    def fetch_results(self, league_code, season_label):
        return self._results

    def fetch_fixtures(self, league_code, season_label):
        return self._fixtures

    def fetch_lineups(self, league_code, season_label):
        return self._lineups

    def fetch_player_stats(self, league_code, season_label):
        return self._player_stats

    def fetch_team_stats(self, league_code, season_label):
        return self._team_stats


# ---------------------------------------------------------------------------
# Router tests
# ---------------------------------------------------------------------------


def test_router_returns_first_non_empty():
    empty = FakeProvider(results=[])
    full = FakeProvider(results=[
        MatchResultDTO(
            league_code="EPL",
            season_label="2023/2024",
            home_team_name="Manchester City",
            away_team_name="Liverpool",
            fixture_date=SAMPLE_DATE,
            home_goals=1,
            away_goals=1,
        )
    ])
    router = IngestionRouter(providers=[empty, full])
    results = router.fetch_results("EPL", "2023/2024")
    assert len(results) == 1
    assert results[0].home_team_name == "Manchester City"


def test_router_skips_unavailable_provider():
    unavailable = UnavailableProvider()
    data = FakeProvider(
        fixtures=[
            FixtureDTO(
                league_code="EPL",
                season_label="2023/2024",
                home_team_name="Arsenal",
                away_team_name="Chelsea",
                fixture_date=SAMPLE_DATE,
            )
        ]
    )
    router = IngestionRouter(providers=[unavailable, data])
    fixtures = router.fetch_fixtures("EPL", "2023/2024")
    assert len(fixtures) == 1


def test_router_falls_through_on_failure():
    fail = AlwaysFailProvider()
    fallback = FakeProvider(
        results=[
            MatchResultDTO(
                league_code="EPL",
                season_label="2023/2024",
                home_team_name="Arsenal",
                away_team_name="Chelsea",
                fixture_date=SAMPLE_DATE,
                home_goals=2,
                away_goals=0,
            )
        ]
    )
    router = IngestionRouter(providers=[fail, fallback])
    results = router.fetch_results("EPL", "2023/2024")
    assert len(results) == 1
    assert results[0].home_goals == 2


def test_router_returns_empty_when_all_fail():
    router = IngestionRouter(providers=[AlwaysFailProvider()])
    assert router.fetch_results("EPL", "2023/2024") == []


def test_router_returns_empty_when_all_unavailable():
    router = IngestionRouter(providers=[UnavailableProvider()])
    assert router.fetch_fixtures("EPL", "2023/2024") == []


# ---------------------------------------------------------------------------
# sync_fixtures tests
# ---------------------------------------------------------------------------


def test_sync_fixtures_creates_teams_and_fixtures(db_session):
    router = IngestionRouter(providers=[
        FakeProvider(fixtures=[
            FixtureDTO(
                league_code="EPL",
                season_label="2023/2024",
                home_team_name="Manchester City",
                away_team_name="Liverpool",
                fixture_date=SAMPLE_DATE,
                status="FINISHED",
                matchweek=13,
            )
        ])
    ])
    count = sync_fixtures(db_session, router, "EPL", "2023/2024")
    assert count == 1

    from temfpa.db.models import Fixture, Team
    fixtures = db_session.query(Fixture).all()
    assert len(fixtures) == 1
    assert fixtures[0].matchweek == 13

    teams = db_session.query(Team).all()
    assert {t.name for t in teams} >= {"Manchester City", "Liverpool"}


def test_sync_fixtures_does_not_duplicate(db_session):
    fixture_dto = FixtureDTO(
        league_code="EPL",
        season_label="2023/2024",
        home_team_name="Arsenal",
        away_team_name="Chelsea",
        fixture_date=SAMPLE_DATE,
        status="FINISHED",
    )
    router = IngestionRouter(providers=[FakeProvider(fixtures=[fixture_dto])])
    sync_fixtures(db_session, router, "EPL", "2023/2024")
    sync_fixtures(db_session, router, "EPL", "2023/2024")

    from temfpa.db.models import Fixture
    assert db_session.query(Fixture).count() == 1


def test_sync_results_writes_winner(db_session):
    router = IngestionRouter(providers=[
        FakeProvider(
            fixtures=[
                FixtureDTO("EPL", "2023/2024", "Manchester City", "Liverpool", SAMPLE_DATE, status="FINISHED"),
            ],
            results=[
                MatchResultDTO("EPL", "2023/2024", "Manchester City", "Liverpool", SAMPLE_DATE, home_goals=2, away_goals=1),
            ],
        )
    ])
    sync_fixtures(db_session, router, "EPL", "2023/2024")
    sync_results(db_session, router, "EPL", "2023/2024")

    from temfpa.db.models import MatchResult
    result = db_session.query(MatchResult).first()
    assert result is not None
    assert result.winner == "home"
    assert result.home_goals == 2


def test_sync_results_draw(db_session):
    router = IngestionRouter(providers=[
        FakeProvider(
            results=[
                MatchResultDTO("EPL", "2023/2024", "Arsenal", "Chelsea", SAMPLE_DATE, home_goals=1, away_goals=1),
            ],
        )
    ])
    sync_results(db_session, router, "EPL", "2023/2024")

    from temfpa.db.models import MatchResult
    result = db_session.query(MatchResult).first()
    assert result.winner == "draw"


# ---------------------------------------------------------------------------
# Team name normalisation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,expected", [
    ("Man United", "Manchester United"),
    ("Man Utd", "Manchester United"),
    ("Manchester Utd", "Manchester United"),
    ("Man City", "Manchester City"),
    ("Tottenham", "Tottenham Hotspur"),
    ("Wolves", "Wolverhampton Wanderers"),
    ("Arsenal", "Arsenal"),  # no alias needed
])
def test_normalise_team_name(raw, expected):
    assert _normalise_team_name(raw) == expected


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


def test_match_result_dto_fields():
    dto = MatchResultDTO(
        league_code="EPL",
        season_label="2023/2024",
        home_team_name="Manchester City",
        away_team_name="Liverpool",
        fixture_date=SAMPLE_DATE,
        home_goals=2,
        away_goals=1,
        home_xg=1.8,
        away_xg=0.9,
    )
    assert dto.home_goals == 2
    assert dto.home_xg == pytest.approx(1.8)


def test_lineup_dto_fields():
    dto = LineupDTO(
        league_code="EPL",
        season_label="2023/2024",
        fixture_date=SAMPLE_DATE,
        home_team_name="Arsenal",
        away_team_name="Chelsea",
        team_name="Arsenal",
        formation="4-3-3",
        is_confirmed=True,
        starters=["Player A", "Player B"],
    )
    assert dto.formation == "4-3-3"
    assert len(dto.starters) == 2
