"""Poisson goal model using linear regression for lambda estimation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

POISSON_FEATURES = [
    "home_goals_scored_5",
    "home_goals_conceded_5",
    "away_goals_scored_5",
    "away_goals_conceded_5",
]

CLAMP_MIN = 0.1
CLAMP_MAX = 6.0


class PoissonGoalModel:
    """Predicts expected goals (lambda) for home and away teams using LinearRegression."""

    def __init__(self) -> None:
        self._home_model = LinearRegression()
        self._away_model = LinearRegression()
        self._fitted = False

    def fit(
        self,
        X: pd.DataFrame,
        home_goals: pd.Series,
        away_goals: pd.Series,
    ) -> "PoissonGoalModel":
        """Fit separate linear regression models for home and away goals.

        Uses POISSON_FEATURES subset of X.
        """
        X_sub = self._extract_features(X)
        self._home_model.fit(X_sub, home_goals)
        self._away_model.fit(X_sub, away_goals)
        self._fitted = True
        return self

    def predict(self, X: pd.DataFrame) -> tuple[float, float]:
        """Return (lambda_home, lambda_away) — expected goals, clamped to [0.1, 6.0]."""
        X_sub = self._extract_features(X)
        if self._fitted:
            lambda_home = float(self._home_model.predict(X_sub)[0])
            lambda_away = float(self._away_model.predict(X_sub)[0])
        else:
            # Realistic defaults based on top-league averages:
            # home teams score ~1.5, away teams ~1.2 goals per game.
            lambda_home = 1.5
            lambda_away = 1.2

        lambda_home = float(np.clip(lambda_home, CLAMP_MIN, CLAMP_MAX))
        lambda_away = float(np.clip(lambda_away, CLAMP_MIN, CLAMP_MAX))
        return lambda_home, lambda_away

    def save(self, path: Path) -> None:
        """Save model to disk using joblib."""
        import joblib
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "home_model": self._home_model,
                "away_model": self._away_model,
                "fitted": self._fitted,
            },
            path,
        )

    def load(self, path: Path) -> "PoissonGoalModel":
        """Load model from disk using joblib."""
        import joblib
        data = joblib.load(Path(path))
        self._home_model = data["home_model"]
        self._away_model = data["away_model"]
        self._fitted = data["fitted"]
        return self

    def _extract_features(self, X: pd.DataFrame) -> pd.DataFrame:
        """Extract POISSON_FEATURES from X, filling missing with 1.0."""
        result = pd.DataFrame(index=X.index)
        for feat in POISSON_FEATURES:
            if feat in X.columns:
                result[feat] = X[feat]
            else:
                result[feat] = 1.0
        return result
