"""MatchHistory adapter — football-data.co.uk CSV downloads.

Provides: historical match results (bulk, fast, reliable).
No API key required. Best for historical backfill.
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

# soccerdata MatchHistory league strings
LEAGUE_MAP: dict[str, str] = {
    "EPL": "ENG-Premier League",
    "ESP1": "ESP-La Liga",
    "GER1": "GER-Bundesliga",
    "ITA1": "ITA-Serie A",
    "FRA1": "FRA-Ligue 1",
}


class MatchHistoryAdapter:
    """Wraps soccerdata.MatchHistory (football-data.co.uk CSVs)."""

    name = "matchhistory"

    def is_available(self) -> bool:
        try:
            import soccerdata  # noqa: F401
            return hasattr(soccerdata, "MatchHistory")
        except ImportError:
            return False

    def _get_league(self, league_code: str) -> str:
        if league_code not in LEAGUE_MAP:
            raise ProviderError(
                f"League '{league_code}' not supported by MatchHistory adapter"
            )
        return LEAGUE_MAP[league_code]

    def fetch_results(self, league_code: str, season_label: str) -> list[MatchResultDTO]:
        import soccerdata as sd

        league = self._get_league(league_code)
        try:
            mh = sd.MatchHistory(leagues=league, seasons=season_label)
            df = mh.read_games().reset_index()
        except Exception as exc:
            raise ProviderError(f"MatchHistory fetch_results failed: {exc}") from exc

        results: list[MatchResultDTO] = []
        for _, row in df.iterrows():
            home_g = row.get("home_goals", row.get("FTHG"))
            away_g = row.get("away_goals", row.get("FTAG"))
            if pd.isna(home_g) or pd.isna(away_g):
                continue

            try:
                fixture_date = pd.to_datetime(row.get("date", row.get("Date"))).to_pydatetime()
            except Exception:
                continue

            home_name = str(row.get("home_team", row.get("HomeTeam", "")))
            away_name = str(row.get("away_team", row.get("AwayTeam", "")))

            results.append(
                MatchResultDTO(
                    league_code=league_code,
                    season_label=season_label,
                    home_team_name=home_name,
                    away_team_name=away_name,
                    fixture_date=fixture_date,
                    home_goals=int(home_g),
                    away_goals=int(away_g),
                )
            )
        return results

    def fetch_fixtures(self, league_code: str, season_label: str) -> list[FixtureDTO]:
        # MatchHistory only has completed matches
        results = self.fetch_results(league_code, season_label)
        return [
            FixtureDTO(
                league_code=r.league_code,
                season_label=r.season_label,
                home_team_name=r.home_team_name,
                away_team_name=r.away_team_name,
                fixture_date=r.fixture_date,
                status="FINISHED",
            )
            for r in results
        ]

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
