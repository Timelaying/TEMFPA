import pandas as pd
import pytest

from temfpa.retrieval import get_match_results, get_team_position


LEAGUE_TABLES = {
    ("ENG-Premier League", "2023/2024"): pd.DataFrame(
        {
            "team": ["Manchester City", "Liverpool", "Arsenal"],
            "points": [91, 82, 80],
        }
    ),
    ("ENG-Premier League", "2022/2023"): pd.DataFrame(
        {
            "team": ["Arsenal", "Manchester City", "Liverpool"],
            "points": [89, 88, 75],
        }
    ),
    ("ESP-La Liga", "2023/2024"): pd.DataFrame(
        {
            "team": ["Real Madrid", "Barcelona", "Girona"],
            "points": [95, 85, 81],
        }
    ),
}

SCHEDULES = {
    ("ENG-Premier League", "2023/2024"): pd.DataFrame(
        {
            "home_team": ["Manchester City", "Liverpool", "Arsenal"],
            "away_team": ["Liverpool", "Manchester City", "Chelsea"],
            "home_score": [2, 1, 0],
            "away_score": [1, 1, 2],
        }
    ),
    ("ENG-Premier League", "2022/2023"): pd.DataFrame(
        {
            "home_team": ["Liverpool", "Manchester City"],
            "away_team": ["Manchester City", "Liverpool"],
            "home_score": [pd.NA, 4],
            "away_score": [pd.NA, 1],
        }
    ),
    ("ESP-La Liga", "2023/2024"): pd.DataFrame(
        {
            "home_team": ["Real Madrid", "Barcelona"],
            "away_team": ["Barcelona", "Real Madrid"],
            "home_score": [3, 1],
            "away_score": [2, 2],
        }
    ),
}


class FakeFotMob:
    calls: list[tuple[str, str]] = []

    def __init__(self, leagues, seasons):
        self.leagues = leagues
        self.seasons = seasons
        self.calls.append((leagues, seasons))

    def read_league_table(self):
        return LEAGUE_TABLES[(self.leagues, self.seasons)].copy()

    def read_schedule(self):
        return SCHEDULES[(self.leagues, self.seasons)].copy()


@pytest.fixture(autouse=True)
def patch_fotmob(monkeypatch):
    FakeFotMob.calls = []
    monkeypatch.setattr("temfpa.retrieval.sd.FotMob", FakeFotMob)


def test_get_team_position_combines_multiple_seasons_with_positions():
    df = get_team_position(
        "Manchester City",
        leagues="ENG-Premier League",
        seasons=["2023/2024", "2022/2023"],
    )

    assert list(df["team"]) == ["Manchester City", "Manchester City"]
    assert list(df["position"]) == [1, 2]
    assert list(df["season"]) == ["2023/2024", "2022/2023"]
    assert FakeFotMob.calls == [
        ("ENG-Premier League", "2023/2024"),
        ("ENG-Premier League", "2022/2023"),
    ]


@pytest.mark.parametrize(
    ("league", "team_name", "expected_team", "expected_position"),
    [
        ("ESP-La Liga", "Real Madrid", "Real Madrid", 1),
        ("ESP-La Liga", "Atletico Madrid", None, None),
    ],
)
def test_get_team_position_handles_different_leagues_and_missing_team(
    league, team_name, expected_team, expected_position
):
    df = get_team_position(team_name, leagues=league, seasons=["2023/2024"])

    if expected_team is None:
        assert df.empty
        assert "season" in df.columns
        assert FakeFotMob.calls == [(league, "2023/2024")]
        return

    assert df.to_dict("records") == [
        {
            "team": expected_team,
            "points": 95,
            "position": expected_position,
            "season": "2023/2024",
        }
    ]


def test_get_match_results_combines_seasons_and_tracks_winner_states():
    df = get_match_results(
        "Manchester City",
        "Liverpool",
        leagues="ENG-Premier League",
        seasons=["2023/2024", "2022/2023"],
    )

    assert len(df) == 4
    assert list(df["season"]) == ["2023/2024", "2023/2024", "2022/2023", "2022/2023"]
    assert list(df["winner"][:2]) == ["Manchester City", "Draw"]
    assert pd.isna(df.loc[2, "winner"])
    assert df.loc[3, "winner"] == "Manchester City"
    assert FakeFotMob.calls == [
        ("ENG-Premier League", "2023/2024"),
        ("ENG-Premier League", "2022/2023"),
    ]


def test_get_match_results_returns_empty_dataframe_when_no_fixture_exists():
    df = get_match_results(
        "Real Madrid",
        "Girona",
        leagues="ESP-La Liga",
        seasons=["2023/2024"],
    )

    assert df.empty
    assert FakeFotMob.calls == [("ESP-La Liga", "2023/2024")]
