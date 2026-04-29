import pandas as pd

from temfpa.analytics import add_match_metrics, export_results, predict_match_outcomes


def test_add_match_metrics_adds_goal_and_xg_columns():
    df = pd.DataFrame(
        {
            "home_score": [2, 1, 0],
            "away_score": [1, 1, 2],
            "winner": ["A", "Draw", "B"],
        }
    )

    out = add_match_metrics(df)

    assert "goal_difference" in out.columns
    assert "total_goals" in out.columns
    assert "home_xg" in out.columns
    assert "away_xg" in out.columns
    assert list(out["total_goals"]) == [3, 2, 2]


def test_predict_match_outcomes_returns_expected_keys():
    df = pd.DataFrame(
        {
            "home_score": [2, 0, 1, 3, 2, 0, 1, 4],
            "away_score": [1, 2, 1, 0, 2, 3, 0, 1],
            "winner": ["A", "B", "Draw", "A", "Draw", "B", "A", "A"],
        }
    )

    result = predict_match_outcomes(df)

    assert "logistic_regression_accuracy" in result
    assert "random_forest_accuracy" in result


def test_export_results_to_csv_and_excel(tmp_path):
    df = pd.DataFrame({"team": ["A"], "points": [3]})
    csv_path = export_results(df, tmp_path / "out.csv")
    assert csv_path.exists()

    try:
        import openpyxl  # noqa: F401
    except Exception:  # noqa: BLE001
        return

    xlsx_path = export_results(df, tmp_path / "out.xlsx")
    assert xlsx_path.exists()
