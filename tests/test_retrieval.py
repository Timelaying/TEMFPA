import pandas as pd
import pytest

from temfpa.retrieval import DataCache, get_match_results, get_team_position


# FBref-format schedules: scores use en-dash (–), no pre-split home_score/away_score.
# 2023/2024: Man City W1 D1 (4 pts) → position 1; 2022/2023: Arsenal W2 (6 pts) > Man City W1 (3 pts) → Man City position 2.
SCHEDULES = {
    ("ENG-Premier League", "2023/2024"): pd.DataFrame(
        {
            "home_team": ["Manchester City", "Liverpool", "Arsenal"],
            "away_team": ["Liverpool", "Manchester City", "Chelsea"],
            "score": ["2\u20131", "1\u20131", "0\u20132"],
        }
    ),
    ("ENG-Premier League", "2022/2023"): pd.DataFrame(
        {
            "home_team": ["Arsenal", "Arsenal", "Liverpool", "Manchester City"],
            "away_team": ["Liverpool", "Chelsea", "Manchester City", "Liverpool"],
            "score": ["3\u20130", "2\u20130", pd.NA, "4\u20131"],
        }
    ),
    ("ESP-La Liga", "2023/2024"): pd.DataFrame(
        {
            "home_team": ["Real Madrid", "Barcelona"],
            "away_team": ["Barcelona", "Real Madrid"],
            "score": ["3\u20132", "1\u20132"],
        }
    ),
}


class FakeFBref:
    calls: list[tuple[str, str]] = []

    def __init__(self, leagues, seasons):
        self.leagues = leagues
        self.seasons = seasons
        self.calls.append((leagues, seasons))

    def read_schedule(self):
        return SCHEDULES[(self.leagues, self.seasons)].copy()


@pytest.fixture(autouse=True)
def patch_fbref(monkeypatch):
    FakeFBref.calls = []
    monkeypatch.setattr("temfpa.retrieval.sd.FBref", FakeFBref)


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "cache"


def test_get_team_position_combines_multiple_seasons_with_positions(cache_dir):
    df = get_team_position(
        "Manchester City",
        leagues="ENG-Premier League",
        seasons=["2023/2024", "2022/2023"],
        cache_dir=cache_dir,
    )

    assert list(df["team"]) == ["Manchester City", "Manchester City"]
    assert list(df["position"]) == [1, 2]
    assert list(df["season"]) == ["2023/2024", "2022/2023"]
    assert FakeFBref.calls == [
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
    cache_dir, league, team_name, expected_team, expected_position
):
    df = get_team_position(team_name, leagues=league, seasons=["2023/2024"], cache_dir=cache_dir)

    if expected_team is None:
        assert df.empty
        assert "season" in df.columns
        assert FakeFBref.calls == [(league, "2023/2024")]
        return

    assert len(df) == 1
    assert df.iloc[0]["team"] == expected_team
    assert df.iloc[0]["position"] == expected_position
    assert df.iloc[0]["season"] == "2023/2024"


def test_get_match_results_combines_seasons_and_tracks_winner_states(cache_dir):
    df = get_match_results(
        "Manchester City",
        "Liverpool",
        leagues="ENG-Premier League",
        seasons=["2023/2024", "2022/2023"],
        cache_dir=cache_dir,
    )

    assert len(df) == 4
    assert list(df["season"]) == ["2023/2024", "2023/2024", "2022/2023", "2022/2023"]
    assert list(df["winner"][:2]) == ["Manchester City", "Draw"]
    assert pd.isna(df.loc[2, "winner"])
    assert df.loc[3, "winner"] == "Manchester City"
    assert FakeFBref.calls == [
        ("ENG-Premier League", "2023/2024"),
        ("ENG-Premier League", "2022/2023"),
    ]


def test_get_match_results_returns_empty_dataframe_when_no_fixture_exists(cache_dir):
    df = get_match_results(
        "Real Madrid",
        "Girona",
        leagues="ESP-La Liga",
        seasons=["2023/2024"],
        cache_dir=cache_dir,
    )

    assert df.empty
    assert FakeFBref.calls == [("ESP-La Liga", "2023/2024")]


class ErrorFBref(FakeFBref):
    def read_schedule(self):
        if self.seasons == "2022/2023":
            raise RuntimeError("network failure")
        return super().read_schedule()


def test_get_team_position_skips_season_when_fetch_fails(monkeypatch, cache_dir):
    FakeFBref.calls = []
    monkeypatch.setattr("temfpa.retrieval.sd.FBref", ErrorFBref)

    df = get_team_position(
        "Manchester City",
        leagues="ENG-Premier League",
        seasons=["2023/2024", "2022/2023"],
        cache_dir=cache_dir,
    )

    assert list(df["team"]) == ["Manchester City"]
    assert list(df["season"]) == ["2023/2024"]
    assert FakeFBref.calls == [
        ("ENG-Premier League", "2023/2024"),
        ("ENG-Premier League", "2022/2023"),
    ]


def test_get_match_results_skips_season_when_fetch_fails(monkeypatch, cache_dir):
    FakeFBref.calls = []
    monkeypatch.setattr("temfpa.retrieval.sd.FBref", ErrorFBref)

    df = get_match_results(
        "Manchester City",
        "Liverpool",
        leagues="ENG-Premier League",
        seasons=["2023/2024", "2022/2023"],
        cache_dir=cache_dir,
    )

    assert len(df) == 2
    assert list(df["season"]) == ["2023/2024", "2023/2024"]
    assert FakeFBref.calls == [
        ("ENG-Premier League", "2023/2024"),
        ("ENG-Premier League", "2022/2023"),
    ]


def test_cache_is_reused_for_positions(cache_dir):
    first = get_team_position(
        "Manchester City",
        leagues="ENG-Premier League",
        seasons=["2023/2024"],
        cache_dir=cache_dir,
    )
    assert len(first) == 1
    assert FakeFBref.calls == [("ENG-Premier League", "2023/2024")]

    FakeFBref.calls = []
    second = get_team_position(
        "Manchester City",
        leagues="ENG-Premier League",
        seasons=["2023/2024"],
        cache_dir=cache_dir,
    )

    assert len(second) == 1
    assert FakeFBref.calls == []


def test_offline_mode_reads_cached_schedule_without_network(cache_dir):
    online = get_match_results(
        "Manchester City",
        "Liverpool",
        leagues="ENG-Premier League",
        seasons=["2023/2024"],
        cache_dir=cache_dir,
    )
    assert len(online) == 2

    FakeFBref.calls = []
    offline = get_match_results(
        "Manchester City",
        "Liverpool",
        leagues="ENG-Premier League",
        seasons=["2023/2024"],
        cache_dir=cache_dir,
        offline=True,
    )

    assert len(offline) == 2
    assert FakeFBref.calls == []


def test_offline_mode_without_cache_returns_empty_data(cache_dir):
    df = get_team_position(
        "Manchester City",
        leagues="ENG-Premier League",
        seasons=["2023/2024"],
        cache_dir=cache_dir,
        offline=True,
    )

    assert df.empty
    assert FakeFBref.calls == []


def test_sqlite_cache_is_reused_for_positions(tmp_path):
    db_path = tmp_path / "temfpa.sqlite"

    first = get_team_position(
        "Manchester City",
        leagues="ENG-Premier League",
        seasons=["2023/2024"],
        db_path=db_path,
    )
    assert len(first) == 1
    assert FakeFBref.calls == [("ENG-Premier League", "2023/2024")]

    FakeFBref.calls = []
    second = get_team_position(
        "Manchester City",
        leagues="ENG-Premier League",
        seasons=["2023/2024"],
        db_path=db_path,
        offline=True,
    )

    assert len(second) == 1
    assert FakeFBref.calls == []
    assert db_path.exists()


def test_data_cache_uses_env_db_path(monkeypatch, tmp_path):
    db_path = tmp_path / "env-cache.sqlite"
    monkeypatch.setenv("TEMFPA_DB_PATH", str(db_path))

    cache = DataCache()
    cache.save(
        "schedule",
        "ENG-Premier League",
        "2023/2024",
        SCHEDULES[("ENG-Premier League", "2023/2024")],
    )

    loaded = cache.load("schedule", "ENG-Premier League", "2023/2024")

    assert loaded is not None
    assert loaded.equals(SCHEDULES[("ENG-Premier League", "2023/2024")])
    assert db_path.exists()
