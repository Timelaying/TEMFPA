import pandas as pd

from temfpa.retrieval import get_match_results, get_team_position


class FakeFotMob:
    def __init__(self, leagues, seasons):
        self.leagues = leagues
        self.seasons = seasons

    def read_league_table(self):
        return pd.DataFrame(
            {
                "team": ["Manchester City", "Liverpool"],
                "points": [89, 82],
            }
        )

    def read_schedule(self):
        return pd.DataFrame(
            {
                "home_team": ["Manchester City", "Liverpool", "Arsenal"],
                "away_team": ["Liverpool", "Manchester City", "Chelsea"],
                "home_score": [2, 1, 0],
                "away_score": [1, 1, 2],
            }
        )


def test_get_team_position(monkeypatch):
    monkeypatch.setattr("temfpa.retrieval.sd.FotMob", FakeFotMob)

    df = get_team_position("Manchester City", seasons=["2023/2024", "2022/2023"])

    assert list(df["team"]) == ["Manchester City", "Manchester City"]
    assert list(df["position"]) == [1, 1]
    assert list(df["season"]) == ["2023/2024", "2022/2023"]


def test_get_match_results(monkeypatch):
    monkeypatch.setattr("temfpa.retrieval.sd.FotMob", FakeFotMob)

    df = get_match_results("Manchester City", "Liverpool", seasons=["2023/2024"])

    assert len(df) == 2
    assert set(df["winner"]) == {"Manchester City", "Draw"}
    assert set(df["season"]) == {"2023/2024"}
