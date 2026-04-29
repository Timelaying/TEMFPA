"""Analysis, modeling, visualization, and export helpers for TEMFPA."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from temfpa.retrieval import get_match_results


FEATURE_COLUMNS = ["home_score", "away_score", "goal_difference", "total_goals"]


def add_match_metrics(matches: pd.DataFrame) -> pd.DataFrame:
    """Add derived metrics for goals and expected goals proxies."""
    if matches.empty:
        return matches.copy()

    df = matches.copy()
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")
    df["goal_difference"] = df["home_score"] - df["away_score"]
    df["total_goals"] = df["home_score"] + df["away_score"]
    # xG proxy based on historical scoring averages when provider xG is unavailable.
    df["home_xg"] = df["home_score"].rolling(3, min_periods=1).mean()
    df["away_xg"] = df["away_score"].rolling(3, min_periods=1).mean()
    return df


def predict_match_outcomes(matches: pd.DataFrame) -> dict[str, float]:
    """Train Logistic Regression and Random Forest models and return accuracies."""
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score
        from sklearn.model_selection import train_test_split
    except Exception:  # noqa: BLE001
        return {"logistic_regression_accuracy": 0.0, "random_forest_accuracy": 0.0}

    df = add_match_metrics(matches)
    if df.empty:
        return {"logistic_regression_accuracy": 0.0, "random_forest_accuracy": 0.0}

    target = df["winner"].fillna("Unknown")
    model_df = df.loc[target != "Unknown", FEATURE_COLUMNS].dropna()
    y = target.loc[model_df.index]

    if len(model_df) < 4 or len(y.unique()) < 2:
        return {"logistic_regression_accuracy": 0.0, "random_forest_accuracy": 0.0}

    x_train, x_test, y_train, y_test = train_test_split(
        model_df, y, test_size=0.25, random_state=42, stratify=y
    )

    lr = LogisticRegression(max_iter=1000)
    lr.fit(x_train, y_train)
    lr_pred = lr.predict(x_test)

    rf = RandomForestClassifier(n_estimators=200, random_state=42)
    rf.fit(x_train, y_train)
    rf_pred = rf.predict(x_test)

    return {
        "logistic_regression_accuracy": float(accuracy_score(y_test, lr_pred)),
        "random_forest_accuracy": float(accuracy_score(y_test, rf_pred)),
    }


def batch_head_to_head(
    team_pairs: Iterable[tuple[str, str]],
    *,
    leagues: str,
    seasons: Iterable[str],
    cache_dir: str | Path | None = None,
    offline: bool = False,
) -> pd.DataFrame:
    """Run head-to-head analysis for multiple team pairs."""
    frames: list[pd.DataFrame] = []
    for team1, team2 in team_pairs:
        matches = get_match_results(
            team1,
            team2,
            leagues=leagues,
            seasons=seasons,
            cache_dir=cache_dir,
            offline=offline,
        )
        metrics = add_match_metrics(matches)
        if metrics.empty:
            continue
        metrics["team1"] = team1
        metrics["team2"] = team2
        frames.append(metrics)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def export_results(df: pd.DataFrame, path: str | Path) -> Path:
    """Export analysis results to CSV or Excel based on extension."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.suffix.lower() == ".csv":
        df.to_csv(output_path, index=False)
    elif output_path.suffix.lower() in {".xlsx", ".xls"}:
        df.to_excel(output_path, index=False)
    else:
        raise ValueError("Unsupported export format. Use .csv, .xlsx, or .xls")

    return output_path


def plot_head_to_head_goals(df: pd.DataFrame, path: str | Path) -> Path:
    """Plot goals by fixture and save chart."""
    if df.empty:
        raise ValueError("No rows to plot.")

    import matplotlib.pyplot as plt

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    plot_df = df.reset_index(drop=True)
    plt.figure(figsize=(10, 5))
    plt.plot(plot_df.index, plot_df["home_score"], marker="o", label="Home Goals")
    plt.plot(plot_df.index, plot_df["away_score"], marker="o", label="Away Goals")
    plt.title("Head-to-head goals")
    plt.xlabel("Fixture index")
    plt.ylabel("Goals")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out)
    plt.close()
    return out
