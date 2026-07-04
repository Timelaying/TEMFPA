"""Sofascore adapter — fast fallback for schedule and standings.

Provides: fixtures, results (no player stats or lineups).
No API key required.
"""

from __future__ import annotations

import logging

import pandas as pd

from temfpa.ingestion.base import (
    FixtureDTO,
    LineupDTO,
    MatchResultDTO,
    PlayerMatchStatDTO,
    ProviderError,
    TeamMatchStatDTO,
)

logger = logging.getLogger(__name__)

LEAGUE_MAP: dict[str, str] = {
    "EPL": "ENG-Premier League",
    "ESP1": "ESP-La Liga",
    "GER1": "GER-Bundesliga",
    "ITA1": "ITA-Serie A",
    "FRA1": "FRA-Ligue 1",
}


class SofascoreAdapter:
    """Wraps soccerdata.Sofascore to implement the DataProvider protocol."""

    name = "sofascore"

    def is_available(self) -> bool:
        try:
            import soccerdata  # noqa: F401
            return hasattr(soccerdata, "Sofascore")
        except ImportError:
            return False

    def _get_league(self, league_code: str) -> str:
        if league_code not in LEAGUE_MAP:
            raise ProviderError(f"League '{league_code}' not supported by Sofascore adapter")
        return LEAGUE_MAP[league_code]

    def fetch_results(self, league_code: str, season_label: str) -> list[MatchResultDTO]:
        import soccerdata as sd

        league = self._get_league(league_code)
        try:
            ss = sd.Sofascore(leagues=league, seasons=season_label)
            schedule = ss.read_schedule().reset_index()
        except Exception as exc:
            raise ProviderError(f"Sofascore fetch_results failed: {exc}") from exc

        results: list[MatchResultDTO] = []
        for _, row in schedule.iterrows():
            home_g = row.get("home_score")
            away_g = row.get("away_score")
            if pd.isna(home_g) or pd.isna(away_g):
                continue

            try:
                fixture_date = pd.to_datetime(row.get("date")).to_pydatetime()
            except Exception:
                continue

            results.append(
                MatchResultDTO(
                    league_code=league_code,
                    season_label=season_label,
                    home_team_name=str(row.get("home_team", "")),
                    away_team_name=str(row.get("away_team", "")),
                    fixture_date=fixture_date,
                    home_goals=int(home_g),
                    away_goals=int(away_g),
                )
            )
        return results

    def fetch_fixtures(self, league_code: str, season_label: str) -> list[FixtureDTO]:
        import soccerdata as sd

        league = self._get_league(league_code)
        try:
            ss = sd.Sofascore(leagues=league, seasons=season_label)
            schedule = ss.read_schedule().reset_index()
        except Exception as exc:
            raise ProviderError(f"Sofascore fetch_fixtures failed: {exc}") from exc

        fixtures: list[FixtureDTO] = []
        for _, row in schedule.iterrows():
            try:
                fixture_date = pd.to_datetime(row.get("date")).to_pydatetime()
            except Exception:
                continue

            home_g = row.get("home_score")
            status = "FINISHED" if pd.notna(home_g) else "SCHEDULED"

            fixtures.append(
                FixtureDTO(
                    league_code=league_code,
                    season_label=season_label,
                    home_team_name=str(row.get("home_team", "")),
                    away_team_name=str(row.get("away_team", "")),
                    fixture_date=fixture_date,
                    status=status,
                )
            )
        return fixtures

    # Sofascore does not provide lineup or per-player/team stats
    def fetch_lineups(self, league_code: str, season_label: str) -> list[LineupDTO]:
        return []

    def fetch_player_stats(
        self, league_code: str, season_label: str
    ) -> list[PlayerMatchStatDTO]:
        return []

    def fetch_team_stats(
        self, league_code: str, season_label: str
    ) -> list[TeamMatchStatDTO]:
        return []
