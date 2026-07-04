"""football-data.org adapter — free API supporting UEFA Champions League.

Requires a free API key from https://www.football-data.org/client/register
Set it in your .env file:  FOOTBALL_DATA_KEY=your_key_here

Free tier: 10 calls/min, covers UCL, EPL, La Liga, Bundesliga, Serie A, Ligue 1.
"""

from __future__ import annotations

import datetime
import logging
import time

from temfpa.ingestion.base import (
    FixtureDTO,
    MatchResultDTO,
    ProviderError,
)

logger = logging.getLogger(__name__)

# Maps our internal league codes to football-data.org competition codes
LEAGUE_MAP: dict[str, str] = {
    "UCL": "CL",
    "EPL": "PL",
    "LA_LIGA": "PD",
    "BUNDESLIGA": "BL1",
    "SERIE_A": "SA",
    "LIGUE_1": "FL1",
}

# Maps football-data.org season year to our label.
# football-data.org uses the start year: 2023 → "2023/2024"
def _season_label(start_year: int) -> str:
    return f"{start_year}/{start_year + 1}"


def _season_year(label: str) -> int:
    """Convert "2023/2024" → 2023."""
    try:
        return int(label.split("/")[0])
    except (ValueError, IndexError):
        return datetime.date.today().year


STATUS_MAP = {
    "FINISHED": "FINISHED",
    "SCHEDULED": "SCHEDULED",
    "LIVE": "LIVE",
    "IN_PLAY": "LIVE",
    "PAUSED": "LIVE",
    "POSTPONED": "POSTPONED",
    "CANCELLED": "CANCELLED",
    "SUSPENDED": "POSTPONED",
    "AWARDED": "FINISHED",
}


class FootballDataOrgAdapter:
    """Fetches fixtures and results from the football-data.org v4 API."""

    name = "football_data_org"
    BASE_URL = "https://api.football-data.org/v4"

    def __init__(self) -> None:
        from temfpa.config import settings
        self._key = settings.FOOTBALL_DATA_KEY

    def is_available(self) -> bool:
        return bool(self._key)

    def _get(self, path: str) -> dict:
        """Make an authenticated GET request. Retries once on 429."""
        try:
            import requests
        except ImportError:
            raise ProviderError("requests library not installed")

        headers = {"X-Auth-Token": self._key}
        url = f"{self.BASE_URL}{path}"
        resp = requests.get(url, headers=headers, timeout=15)

        if resp.status_code == 429:
            # Rate limited — wait 65 seconds and retry once
            logger.warning("football-data.org rate limit hit, waiting 65s...")
            time.sleep(65)
            resp = requests.get(url, headers=headers, timeout=15)

        if not resp.ok:
            raise ProviderError(
                f"football-data.org API error {resp.status_code}: {resp.text[:200]}"
            )
        return resp.json()

    def _competition_code(self, league_code: str) -> str:
        code = LEAGUE_MAP.get(league_code)
        if not code:
            raise ProviderError(
                f"League '{league_code}' not supported by football-data.org adapter"
            )
        return code

    def fetch_fixtures(self, league_code: str, season_label: str) -> list[FixtureDTO]:
        comp = self._competition_code(league_code)
        year = _season_year(season_label)
        try:
            data = self._get(f"/competitions/{comp}/matches?season={year}")
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"fetch_fixtures failed: {exc}") from exc

        fixtures: list[FixtureDTO] = []
        for match in data.get("matches", []):
            try:
                fixture_date = datetime.datetime.fromisoformat(
                    match["utcDate"].replace("Z", "+00:00")
                ).replace(tzinfo=None)
            except (KeyError, ValueError):
                continue

            home_name = match.get("homeTeam", {}).get("name", "")
            away_name = match.get("awayTeam", {}).get("name", "")
            if not home_name or not away_name:
                continue

            raw_status = match.get("status", "SCHEDULED")
            status = STATUS_MAP.get(raw_status, "SCHEDULED")
            matchweek = match.get("matchday")

            fixtures.append(
                FixtureDTO(
                    league_code=league_code,
                    season_label=season_label,
                    home_team_name=home_name,
                    away_team_name=away_name,
                    fixture_date=fixture_date,
                    status=status,
                    matchweek=matchweek,
                    provider_ids={"football_data_org": str(match.get("id", ""))},
                )
            )
        return fixtures

    def fetch_results(self, league_code: str, season_label: str) -> list[MatchResultDTO]:
        comp = self._competition_code(league_code)
        year = _season_year(season_label)
        try:
            data = self._get(f"/competitions/{comp}/matches?season={year}&status=FINISHED")
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"fetch_results failed: {exc}") from exc

        results: list[MatchResultDTO] = []
        for match in data.get("matches", []):
            score = match.get("score", {})
            full_time = score.get("fullTime", {})
            home_goals = full_time.get("home")
            away_goals = full_time.get("away")
            if home_goals is None or away_goals is None:
                continue

            try:
                fixture_date = datetime.datetime.fromisoformat(
                    match["utcDate"].replace("Z", "+00:00")
                ).replace(tzinfo=None)
            except (KeyError, ValueError):
                continue

            half_time = score.get("halfTime", {})
            home_name = match.get("homeTeam", {}).get("name", "")
            away_name = match.get("awayTeam", {}).get("name", "")
            if not home_name or not away_name:
                continue

            results.append(
                MatchResultDTO(
                    league_code=league_code,
                    season_label=season_label,
                    home_team_name=home_name,
                    away_team_name=away_name,
                    fixture_date=fixture_date,
                    home_goals=int(home_goals),
                    away_goals=int(away_goals),
                    home_ht_goals=int(half_time["home"]) if half_time.get("home") is not None else None,
                    away_ht_goals=int(half_time["away"]) if half_time.get("away") is not None else None,
                    provider_ids={"football_data_org": str(match.get("id", ""))},
                )
            )
        return results

    # football-data.org free tier does not provide lineups or player stats
    def fetch_lineups(self, league_code: str, season_label: str) -> list:
        return []

    def fetch_player_stats(self, league_code: str, season_label: str) -> list:
        return []

    def fetch_team_stats(self, league_code: str, season_label: str) -> list:
        return []
