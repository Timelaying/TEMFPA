"""Data retrieval helpers for league positions and head-to-head match results."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Iterable

import pandas as pd
import soccerdata as sd


logger = logging.getLogger(__name__)


class DataCache:
    """Simple file-based cache for FotMob tables and schedules."""

    def __init__(self, cache_dir: str | Path | None = None):
        base_dir = cache_dir or os.getenv("TEMFPA_CACHE_DIR", "~/.cache/temfpa")
        self.cache_dir = Path(base_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, category: str, league: str, season: str) -> Path:
        raw_key = f"{category}:{league}:{season}".encode("utf-8")
        key = hashlib.sha256(raw_key).hexdigest()[:16]
        return self.cache_dir / f"{category}_{key}.pkl"

    def load(self, category: str, league: str, season: str) -> pd.DataFrame | None:
        cache_path = self._path_for(category, league, season)
        if not cache_path.exists():
            return None
        return pd.read_pickle(cache_path)

    def save(self, category: str, league: str, season: str, data: pd.DataFrame) -> None:
        cache_path = self._path_for(category, league, season)
        data.to_pickle(cache_path)


def _get_or_fetch(
    cache: DataCache,
    category: str,
    league: str,
    season: str,
    fetcher,
    offline: bool,
) -> pd.DataFrame:
    cached = cache.load(category, league, season)
    if cached is not None:
        logger.info("Loaded %s for %s (%s) from cache.", category, league, season)
        return cached

    if offline:
        raise FileNotFoundError(
            f"Offline mode enabled and no cached {category} exists for {league} {season}."
        )

    fetched = fetcher()
    cache.save(category, league, season, fetched)
    logger.info("Fetched and cached %s for %s (%s).", category, league, season)
    return fetched


def get_team_position(
    team_name: str,
    leagues: str = "ENG-Premier League",
    seasons: Iterable[str] = ("2023/2024",),
    *,
    cache_dir: str | Path | None = None,
    offline: bool = False,
) -> pd.DataFrame:
    """Return league-table rows for a single team across multiple seasons."""
    results: list[pd.DataFrame] = []
    cache = DataCache(cache_dir)

    for season in seasons:
        try:
            league_table = _get_or_fetch(
                cache=cache,
                category="league_table",
                league=leagues,
                season=season,
                fetcher=lambda: sd.FotMob(leagues=leagues, seasons=season)
                .read_league_table()
                .reset_index(drop=True),
                offline=offline,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Failed to fetch league table for league=%s season=%s: %s",
                leagues,
                season,
                exc,
            )
            continue

        league_table["position"] = league_table.index + 1

        team_position = league_table[league_table["team"] == team_name].copy()
        team_position["season"] = season
        results.append(team_position)

    if not results:
        return pd.DataFrame()

    return pd.concat(results, ignore_index=True)


def _get_match_winner(row: pd.Series) -> str | pd.NA:
    """Infer the winner from a schedule row, or return missing when scores are absent."""
    if pd.isna(row["home_score"]) or pd.isna(row["away_score"]):
        return pd.NA

    home_score = int(row["home_score"])
    away_score = int(row["away_score"])

    if home_score > away_score:
        return row["home_team"]
    if home_score < away_score:
        return row["away_team"]
    return "Draw"


def get_match_results(
    team1: str,
    team2: str,
    leagues: str = "ENG-Premier League",
    seasons: Iterable[str] = ("2023/2024",),
    *,
    cache_dir: str | Path | None = None,
    offline: bool = False,
) -> pd.DataFrame:
    """Return all fixtures between two teams and infer winner/draw from scores."""
    match_data: list[dict] = []
    cache = DataCache(cache_dir)

    for season in seasons:
        try:
            schedule = _get_or_fetch(
                cache=cache,
                category="schedule",
                league=leagues,
                season=season,
                fetcher=lambda: sd.FotMob(leagues=leagues, seasons=season).read_schedule(),
                offline=offline,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Failed to fetch match schedule for league=%s season=%s: %s",
                leagues,
                season,
                exc,
            )
            continue

        team_matches = schedule[
            ((schedule["home_team"] == team1) & (schedule["away_team"] == team2))
            | ((schedule["home_team"] == team2) & (schedule["away_team"] == team1))
        ]

        for _, row in team_matches.iterrows():
            match_info = row.to_dict()
            match_info["season"] = season
            match_info["winner"] = _get_match_winner(row)
            match_data.append(match_info)

    return pd.DataFrame(match_data)
