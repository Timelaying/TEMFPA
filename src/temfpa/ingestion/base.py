"""Data Transfer Objects and provider protocol for the ingestion layer."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# DTOs — plain dataclasses, no SQLAlchemy, no pandas
# ---------------------------------------------------------------------------


@dataclass
class LeagueDTO:
    code: str
    name: str
    country: str
    tier: int = 1
    provider_ids: dict = field(default_factory=dict)


@dataclass
class SeasonDTO:
    league_code: str
    label: str               # "2023/2024"
    start_date: datetime.date
    end_date: datetime.date


@dataclass
class TeamDTO:
    name: str
    short_name: str | None = None
    country: str | None = None
    provider_ids: dict = field(default_factory=dict)


@dataclass
class PlayerDTO:
    name: str
    team_name: str
    position: str | None = None
    nationality: str | None = None
    dob: datetime.date | None = None
    provider_ids: dict = field(default_factory=dict)


@dataclass
class FixtureDTO:
    league_code: str
    season_label: str
    home_team_name: str
    away_team_name: str
    fixture_date: datetime.datetime
    venue: str | None = None
    status: str = "SCHEDULED"
    matchweek: int | None = None
    provider_ids: dict = field(default_factory=dict)


@dataclass
class MatchResultDTO:
    league_code: str
    season_label: str
    home_team_name: str
    away_team_name: str
    fixture_date: datetime.datetime
    home_goals: int | None = None
    away_goals: int | None = None
    home_ht_goals: int | None = None
    away_ht_goals: int | None = None
    home_xg: float | None = None
    away_xg: float | None = None
    provider_ids: dict = field(default_factory=dict)


@dataclass
class LineupDTO:
    league_code: str
    season_label: str
    fixture_date: datetime.datetime
    home_team_name: str
    away_team_name: str
    team_name: str
    formation: str | None
    is_confirmed: bool
    starters: list[str] = field(default_factory=list)    # player names
    substitutes: list[str] = field(default_factory=list)


@dataclass
class PlayerMatchStatDTO:
    league_code: str
    season_label: str
    fixture_date: datetime.datetime
    home_team_name: str
    away_team_name: str
    team_name: str
    player_name: str
    minutes_played: int | None = None
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    xg: float | None = None
    xa: float | None = None


@dataclass
class TeamMatchStatDTO:
    league_code: str
    season_label: str
    fixture_date: datetime.datetime
    home_team_name: str
    away_team_name: str
    team_name: str
    formation: str | None = None
    possession: float | None = None
    shots: int | None = None
    shots_on_target: int | None = None
    xg: float | None = None


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class DataProvider(Protocol):
    """Interface every ingestion adapter must implement."""

    name: str

    def is_available(self) -> bool:
        """Return True if this provider can be used (API key present, lib installed, etc.)."""
        ...

    def fetch_results(
        self,
        league_code: str,
        season_label: str,
    ) -> list[MatchResultDTO]:
        """Fetch completed match results for a league/season."""
        ...

    def fetch_fixtures(
        self,
        league_code: str,
        season_label: str,
    ) -> list[FixtureDTO]:
        """Fetch upcoming and recent fixtures."""
        ...

    def fetch_lineups(
        self,
        league_code: str,
        season_label: str,
    ) -> list[LineupDTO]:
        """Fetch lineups and formations for finished matches."""
        ...

    def fetch_player_stats(
        self,
        league_code: str,
        season_label: str,
    ) -> list[PlayerMatchStatDTO]:
        """Fetch per-player per-match statistics."""
        ...

    def fetch_team_stats(
        self,
        league_code: str,
        season_label: str,
    ) -> list[TeamMatchStatDTO]:
        """Fetch per-team per-match statistics."""
        ...


class ProviderError(Exception):
    """Raised when a provider call fails."""
