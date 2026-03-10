"""Data retrieval helpers for league positions and head-to-head match results."""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import soccerdata as sd


def get_team_position(
    team_name: str,
    leagues: str = "ENG-Premier League",
    seasons: Iterable[str] = ("2023/2024",),
) -> pd.DataFrame:
    """Return league-table rows for a single team across multiple seasons."""
    results: list[pd.DataFrame] = []

    for season in seasons:
        fotmob = sd.FotMob(leagues=leagues, seasons=season)
        league_table = fotmob.read_league_table().reset_index(drop=True)
        league_table["position"] = league_table.index + 1

        team_position = league_table[league_table["team"] == team_name].copy()
        team_position.loc[:, "season"] = season
        results.append(team_position)

    if not results:
        return pd.DataFrame()

    return pd.concat(results, ignore_index=True)


def get_match_results(
    team1: str,
    team2: str,
    leagues: str = "ENG-Premier League",
    seasons: Iterable[str] = ("2023/2024",),
) -> pd.DataFrame:
    """Return all fixtures between two teams and infer winner/draw from scores."""
    match_data: list[dict] = []

    for season in seasons:
        fotmob = sd.FotMob(leagues=leagues, seasons=season)
        schedule = fotmob.read_schedule()

        team_matches = schedule[
            ((schedule["home_team"] == team1) & (schedule["away_team"] == team2))
            | ((schedule["home_team"] == team2) & (schedule["away_team"] == team1))
        ]

        for _, row in team_matches.iterrows():
            match_info = row.to_dict()
            match_info["season"] = season

            home_score = int(row["home_score"])
            away_score = int(row["away_score"])

            if home_score > away_score:
                match_info["winner"] = row["home_team"]
            elif home_score < away_score:
                match_info["winner"] = row["away_team"]
            else:
                match_info["winner"] = "Draw"

            match_data.append(match_info)

    return pd.DataFrame(match_data)
