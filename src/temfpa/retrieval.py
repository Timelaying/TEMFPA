"""Data retrieval helpers for league positions and head-to-head match results."""

from __future__ import annotations

import hashlib
import logging
import os
import pickle
import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd
import soccerdata as sd


logger = logging.getLogger(__name__)


def _parse_fbref_schedule(df: pd.DataFrame) -> pd.DataFrame:
    """Add home_score and away_score columns by parsing FBref's 'score' column (e.g. '0–3')."""
    df = df.copy()
    scores = df["score"].str.split("\u2013", expand=True)
    df["home_score"] = pd.to_numeric(scores[0], errors="coerce")
    df["away_score"] = pd.to_numeric(scores[1], errors="coerce")
    return df


def _compute_standings(schedule: pd.DataFrame) -> pd.DataFrame:
    """Derive a league standings table from a parsed FBref schedule DataFrame."""
    teams: dict[str, dict] = {}
    for _, row in schedule.iterrows():
        if pd.isna(row.get("home_score")) or pd.isna(row.get("away_score")):
            continue
        home = row["home_team"]
        away = row["away_team"]
        hs, as_ = int(row["home_score"]), int(row["away_score"])
        for team in (home, away):
            if team not in teams:
                teams[team] = {"team": team, "MP": 0, "W": 0, "D": 0, "L": 0, "GF": 0, "GA": 0, "Pts": 0}
        teams[home]["MP"] += 1
        teams[away]["MP"] += 1
        teams[home]["GF"] += hs
        teams[home]["GA"] += as_
        teams[away]["GF"] += as_
        teams[away]["GA"] += hs
        if hs > as_:
            teams[home]["W"] += 1
            teams[home]["Pts"] += 3
            teams[away]["L"] += 1
        elif hs < as_:
            teams[away]["W"] += 1
            teams[away]["Pts"] += 3
            teams[home]["L"] += 1
        else:
            teams[home]["D"] += 1
            teams[away]["D"] += 1
            teams[home]["Pts"] += 1
            teams[away]["Pts"] += 1
    df = pd.DataFrame(list(teams.values()))
    df = df.sort_values(["Pts", "GF"], ascending=False).reset_index(drop=True)
    return df


class DataCache:
    """Cache FotMob tables and schedules using files or a SQLite database."""

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        db_path: str | Path | None = None,
    ):
        configured_db_path = db_path or os.getenv("TEMFPA_DB_PATH")
        self.db_path = Path(configured_db_path).expanduser() if configured_db_path else None
        self.cache_dir: Path | None = None

        if self.db_path is not None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._initialize_database()
            return

        base_dir = cache_dir or os.getenv("TEMFPA_CACHE_DIR", "~/.cache/temfpa")
        self.cache_dir = Path(base_dir).expanduser()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _initialize_database(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
                    category TEXT NOT NULL,
                    league TEXT NOT NULL,
                    season TEXT NOT NULL,
                    data BLOB NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (category, league, season)
                )
                """
            )

    def _path_for(self, category: str, league: str, season: str) -> Path:
        raw_key = f"{category}:{league}:{season}".encode("utf-8")
        key = hashlib.sha256(raw_key).hexdigest()[:16]
        if self.cache_dir is None:
            raise RuntimeError("File cache path requested while SQLite cache is enabled.")
        return self.cache_dir / f"{category}_{key}.pkl"

    def load(self, category: str, league: str, season: str) -> pd.DataFrame | None:
        if self.db_path is not None:
            with sqlite3.connect(self.db_path) as connection:
                row = connection.execute(
                    """
                    SELECT data FROM cache_entries
                    WHERE category = ? AND league = ? AND season = ?
                    """,
                    (category, league, season),
                ).fetchone()
            if row is None:
                return None
            return pickle.loads(row[0])

        cache_path = self._path_for(category, league, season)
        if not cache_path.exists():
            return None
        return pd.read_pickle(cache_path)

    def save(self, category: str, league: str, season: str, data: pd.DataFrame) -> None:
        if self.db_path is not None:
            payload = pickle.dumps(data)
            with sqlite3.connect(self.db_path) as connection:
                connection.execute(
                    """
                    INSERT OR REPLACE INTO cache_entries (
                        category, league, season, data, created_at, updated_at
                    )
                    VALUES (
                        ?,
                        ?,
                        ?,
                        ?,
                        COALESCE(
                            (
                                SELECT created_at FROM cache_entries
                                WHERE category = ? AND league = ? AND season = ?
                            ),
                            CURRENT_TIMESTAMP
                        ),
                        CURRENT_TIMESTAMP
                    )
                    """,
                    (category, league, season, payload, category, league, season),
                )
            return

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
    db_path: str | Path | None = None,
    offline: bool = False,
) -> pd.DataFrame:
    """Return league-table rows for a single team across multiple seasons."""
    results: list[pd.DataFrame] = []
    cache = DataCache(cache_dir, db_path=db_path)

    for season in seasons:
        try:
            schedule = _get_or_fetch(
                cache=cache,
                category="schedule",
                league=leagues,
                season=season,
                fetcher=lambda: _parse_fbref_schedule(
                    sd.FBref(leagues=leagues, seasons=season).read_schedule().reset_index()
                ),
                offline=offline,
            )
            league_table = _compute_standings(schedule)
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
    db_path: str | Path | None = None,
    offline: bool = False,
) -> pd.DataFrame:
    """Return all fixtures between two teams and infer winner/draw from scores."""
    match_data: list[dict] = []
    cache = DataCache(cache_dir, db_path=db_path)

    for season in seasons:
        try:
            schedule = _get_or_fetch(
                cache=cache,
                category="schedule",
                league=leagues,
                season=season,
                fetcher=lambda: _parse_fbref_schedule(
                    sd.FBref(leagues=leagues, seasons=season).read_schedule().reset_index()
                ),
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
