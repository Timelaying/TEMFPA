"""Ingestion router — tries providers in priority order, falls back gracefully."""

from __future__ import annotations

import logging
from typing import Any

from temfpa.ingestion.base import (
    DataProvider,
    FixtureDTO,
    LineupDTO,
    MatchResultDTO,
    PlayerMatchStatDTO,
    ProviderError,
    TeamMatchStatDTO,
)
from temfpa.ingestion.fbref_adapter import FBrefAdapter
from temfpa.ingestion.matchhistory_adapter import MatchHistoryAdapter
from temfpa.ingestion.sofascore_adapter import SofascoreAdapter

logger = logging.getLogger(__name__)


class NoDataAvailableError(Exception):
    """Raised when all providers fail for a given request."""


class IngestionRouter:
    """Tries each provider in order and returns the first successful response.

    Provider priority (all free, no API key required):
      1. FBref  — richest data (results, lineups, player stats, team stats)
      2. Sofascore — fast fallback for schedule/results
      3. MatchHistory — historical CSV bulk fallback
    """

    def __init__(self, providers: list[DataProvider] | None = None) -> None:
        if providers is None:
            providers = [
                FBrefAdapter(),
                SofascoreAdapter(),
                MatchHistoryAdapter(),
            ]
        self.providers = providers

    def _try_all(self, method: str, *args: Any, **kwargs: Any) -> list:
        """Call `method` on each available provider; return first non-empty result."""
        errors: list[str] = []
        for provider in self.providers:
            if not provider.is_available():
                logger.debug("Provider '%s' not available, skipping.", provider.name)
                continue
            try:
                result = getattr(provider, method)(*args, **kwargs)
                if result:
                    logger.info(
                        "Provider '%s' returned %d records for %s.",
                        provider.name,
                        len(result),
                        method,
                    )
                    return result
                logger.debug("Provider '%s' returned empty result for %s.", provider.name, method)
            except ProviderError as exc:
                logger.warning("Provider '%s' failed for %s: %s", provider.name, method, exc)
                errors.append(f"{provider.name}: {exc}")

        if errors:
            logger.error("All providers failed for %s: %s", method, "; ".join(errors))
        return []

    def fetch_results(self, league_code: str, season_label: str) -> list[MatchResultDTO]:
        return self._try_all("fetch_results", league_code, season_label)

    def fetch_fixtures(self, league_code: str, season_label: str) -> list[FixtureDTO]:
        return self._try_all("fetch_fixtures", league_code, season_label)

    def fetch_lineups(self, league_code: str, season_label: str) -> list[LineupDTO]:
        return self._try_all("fetch_lineups", league_code, season_label)

    def fetch_player_stats(
        self, league_code: str, season_label: str
    ) -> list[PlayerMatchStatDTO]:
        return self._try_all("fetch_player_stats", league_code, season_label)

    def fetch_team_stats(
        self, league_code: str, season_label: str
    ) -> list[TeamMatchStatDTO]:
        return self._try_all("fetch_team_stats", league_code, season_label)
