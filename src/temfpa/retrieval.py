"""Data retrieval helpers for league positions and head-to-head match results."""

from __future__ import annotations

import logging
from typing import Iterable

import pandas as pd
import soccerdata as sd


logger = logging.getLogger(__name__)


def get_team_position(
    team_name: str,
    leagues: str = "ENG-Premier League",
    seasons: Iterable[str] = ("2023/2024",),
) -> pd.DataFrame:
    """Return league-table rows for a single team across multiple seasons."""
    results: list[pd.DataFrame] = []

    for season in seasons:
        try:
            fotmob = sd.FotMob(leagues=leagues, seasons=season)
            league_table = fotmob.read_league_table().reset_index(drop=True)
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
) -> pd.DataFrame:
    """Return all fixtures between two teams and infer winner/draw from scores."""
    match_data: list[dict] = []

    for season in seasons:
        try:
            fotmob = sd.FotMob(leagues=leagues, seasons=season)
            schedule = fotmob.read_schedule()
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
