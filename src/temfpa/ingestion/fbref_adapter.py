"""FBref adapter — primary free data source via the soccerdata library.

Provides: fixtures, results, lineups, formations, player stats, team stats.
No API key required.
"""

from __future__ import annotations

import datetime
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

# FBref league code mapping: our internal code → soccerdata league string
LEAGUE_MAP: dict[str, str] = {
    "EPL": "ENG-Premier League",
    "ESP1": "ESP-La Liga",
    "GER1": "GER-Bundesliga",
    "ITA1": "ITA-Serie A",
    "FRA1": "FRA-Ligue 1",
}


def _fbref_season(label: str) -> str:
    """Convert "2023/2024" → "2324" (FBref season format)."""
    parts = label.split("/")
    if len(parts) == 2:
        return parts[0][-2:] + parts[1][-2:]
    return label


def _parse_score(score: str | float | None) -> tuple[int | None, int | None]:
    """Parse FBref score string '2–1' → (2, 1)."""
    if pd.isna(score) or score is None:
        return None, None
    score_str = str(score)
    for sep in ["\u2013", "-", "–"]:
        if sep in score_str:
            parts = score_str.split(sep)
            try:
                return int(parts[0].strip()), int(parts[1].strip())
            except (ValueError, IndexError):
                return None, None
    return None, None


class FBrefAdapter:
    """Wraps soccerdata.FBref to implement the DataProvider protocol."""

    name = "fbref"

    def is_available(self) -> bool:
        try:
            import soccerdata  # noqa: F401
            return True
        except ImportError:
            return False

    def _get_fbref_league(self, league_code: str) -> str:
        if league_code not in LEAGUE_MAP:
            raise ProviderError(f"League '{league_code}' not supported by FBref adapter")
        return LEAGUE_MAP[league_code]

    def fetch_results(self, league_code: str, season_label: str) -> list[MatchResultDTO]:
        import soccerdata as sd

        fbref_league = self._get_fbref_league(league_code)
        try:
            fbref = sd.FBref(leagues=fbref_league, seasons=season_label)
            schedule = fbref.read_schedule().reset_index()
        except Exception as exc:
            raise ProviderError(f"FBref fetch_results failed: {exc}") from exc

        results: list[MatchResultDTO] = []
        for _, row in schedule.iterrows():
            home_g, away_g = _parse_score(row.get("score"))
            if home_g is None:
                continue  # unplayed fixture

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
                    home_goals=home_g,
                    away_goals=away_g,
                    provider_ids={"fbref": str(row.get("game_id", ""))},
                )
            )
        return results

    def fetch_fixtures(self, league_code: str, season_label: str) -> list[FixtureDTO]:
        import soccerdata as sd

        fbref_league = self._get_fbref_league(league_code)
        try:
            fbref = sd.FBref(leagues=fbref_league, seasons=season_label)
            schedule = fbref.read_schedule().reset_index()
        except Exception as exc:
            raise ProviderError(f"FBref fetch_fixtures failed: {exc}") from exc

        fixtures: list[FixtureDTO] = []
        for _, row in schedule.iterrows():
            try:
                fixture_date = pd.to_datetime(row.get("date")).to_pydatetime()
            except Exception:
                continue

            home_g, _ = _parse_score(row.get("score"))
            status = "FINISHED" if home_g is not None else "SCHEDULED"

            week = row.get("week")
            matchweek = int(week) if pd.notna(week) else None

            fixtures.append(
                FixtureDTO(
                    league_code=league_code,
                    season_label=season_label,
                    home_team_name=str(row.get("home_team", "")),
                    away_team_name=str(row.get("away_team", "")),
                    fixture_date=fixture_date,
                    venue=str(row.get("venue", "")) or None,
                    status=status,
                    matchweek=matchweek,
                    provider_ids={"fbref": str(row.get("game_id", ""))},
                )
            )
        return fixtures

    def fetch_lineups(self, league_code: str, season_label: str) -> list[LineupDTO]:
        import soccerdata as sd

        fbref_league = self._get_fbref_league(league_code)
        try:
            fbref = sd.FBref(leagues=fbref_league, seasons=season_label)
            lineups_df = fbref.read_lineup().reset_index()
        except Exception as exc:
            raise ProviderError(f"FBref fetch_lineups failed: {exc}") from exc

        lineups: list[LineupDTO] = []
        if lineups_df.empty:
            return lineups

        # Group by game and team
        group_cols = [c for c in ["game", "team"] if c in lineups_df.columns]
        if not group_cols:
            return lineups

        for (game, team), grp in lineups_df.groupby(group_cols):
            # Extract home/away teams from the game string "2023-11-25 TeamA-TeamB"
            teams_part = str(game).split(" ", 1)[-1] if " " in str(game) else str(game)
            parts = teams_part.split("-", 1)
            home_name = parts[0].strip() if len(parts) > 1 else ""
            away_name = parts[1].strip() if len(parts) > 1 else ""

            try:
                date_str = str(game).split(" ")[0]
                fixture_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                fixture_date = datetime.datetime.now()

            formation_col = next(
                (c for c in grp.columns if "formation" in c.lower()), None
            )
            formation = str(grp[formation_col].iloc[0]) if formation_col else None

            starter_col = next(
                (c for c in grp.columns if "starter" in c.lower()), None
            )
            player_col = next(
                (c for c in grp.columns if "player" in c.lower()), None
            )

            starters, subs = [], []
            if player_col and starter_col:
                for _, prow in grp.iterrows():
                    pname = str(prow.get(player_col, ""))
                    if prow.get(starter_col):
                        starters.append(pname)
                    else:
                        subs.append(pname)

            lineups.append(
                LineupDTO(
                    league_code=league_code,
                    season_label=season_label,
                    fixture_date=fixture_date,
                    home_team_name=home_name,
                    away_team_name=away_name,
                    team_name=str(team),
                    formation=formation if formation and formation != "nan" else None,
                    is_confirmed=True,
                    starters=starters,
                    substitutes=subs,
                )
            )
        return lineups

    def fetch_player_stats(
        self, league_code: str, season_label: str
    ) -> list[PlayerMatchStatDTO]:
        import soccerdata as sd

        fbref_league = self._get_fbref_league(league_code)
        try:
            fbref = sd.FBref(leagues=fbref_league, seasons=season_label)
            stats_df = fbref.read_player_match_stats(stat_type="summary").reset_index()
        except Exception as exc:
            raise ProviderError(f"FBref fetch_player_stats failed: {exc}") from exc

        result: list[PlayerMatchStatDTO] = []
        if stats_df.empty:
            return result

        for _, row in stats_df.iterrows():
            try:
                fixture_date = pd.to_datetime(row.get("date")).to_pydatetime()
            except Exception:
                continue

            def _int(val: object) -> int:
                try:
                    return int(val) if pd.notna(val) else 0
                except (ValueError, TypeError):
                    return 0

            def _float(val: object) -> float | None:
                try:
                    return float(val) if pd.notna(val) else None
                except (ValueError, TypeError):
                    return None

            result.append(
                PlayerMatchStatDTO(
                    league_code=league_code,
                    season_label=season_label,
                    fixture_date=fixture_date,
                    home_team_name=str(row.get("home_team", "")),
                    away_team_name=str(row.get("away_team", "")),
                    team_name=str(row.get("team", "")),
                    player_name=str(row.get("player", "")),
                    minutes_played=_int(row.get("minutes", row.get("Min"))),
                    goals=_int(row.get("goals", row.get("Gls", 0))),
                    assists=_int(row.get("assists", row.get("Ast", 0))),
                    yellow_cards=_int(row.get("yellow_cards", row.get("CrdY", 0))),
                    red_cards=_int(row.get("red_cards", row.get("CrdR", 0))),
                    xg=_float(row.get("xg", row.get("xG"))),
                    xa=_float(row.get("xa", row.get("xA"))),
                )
            )
        return result

    def fetch_team_stats(
        self, league_code: str, season_label: str
    ) -> list[TeamMatchStatDTO]:
        import soccerdata as sd

        fbref_league = self._get_fbref_league(league_code)
        try:
            fbref = sd.FBref(leagues=fbref_league, seasons=season_label)
            stats_df = fbref.read_team_match_stats(stat_type="summary").reset_index()
        except Exception as exc:
            raise ProviderError(f"FBref fetch_team_stats failed: {exc}") from exc

        result: list[TeamMatchStatDTO] = []
        if stats_df.empty:
            return result

        for _, row in stats_df.iterrows():
            try:
                fixture_date = pd.to_datetime(row.get("date")).to_pydatetime()
            except Exception:
                continue

            def _int(val: object) -> int | None:
                try:
                    return int(val) if pd.notna(val) else None
                except (ValueError, TypeError):
                    return None

            def _float(val: object) -> float | None:
                try:
                    return float(val) if pd.notna(val) else None
                except (ValueError, TypeError):
                    return None

            result.append(
                TeamMatchStatDTO(
                    league_code=league_code,
                    season_label=season_label,
                    fixture_date=fixture_date,
                    home_team_name=str(row.get("home_team", "")),
                    away_team_name=str(row.get("away_team", "")),
                    team_name=str(row.get("team", "")),
                    possession=_float(row.get("possession", row.get("Poss"))),
                    shots=_int(row.get("shots", row.get("Sh"))),
                    shots_on_target=_int(row.get("shots_on_target", row.get("SoT"))),
                    xg=_float(row.get("xg", row.get("xG"))),
                )
            )
        return result
