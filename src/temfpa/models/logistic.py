"""Logistic regression predictor for match outcome classification."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler


class LogisticPredictor:
    """Logistic regression classifier for match outcome (0=home, 1=draw, 2=away)."""

    def __init__(self) -> None:
        self._model = LogisticRegression(
            max_iter=1000,
            multi_class="multinomial",
            solver="lbfgs",
            C=1.0,
            random_state=42,
        )
        self._scaler = StandardScaler()
        self._fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "LogisticPredictor":
        """Fit the model. y in {0=home, 1=draw, 2=away}."""
        X_scaled = self._scaler.fit_transform(X.values.astype(float))
        self._model.fit(X_scaled, y)
        self._fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return shape (N, 3) probability array."""
        if not self._fitted:
            n = len(X)
            return np.full((n, 3), 1.0 / 3.0)
        X_scaled = self._scaler.transform(X.values.astype(float))
        return self._model.predict_proba(X_scaled)

    def save(self, path: Path) -> None:
        """Save model to disk using joblib."""
        import joblib
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self._model,
                "scaler": self._scaler,
                "fitted": self._fitted,
            },
            path,
        )

    def load(self, path: Path) -> "LogisticPredictor":
        """Load model from disk."""
        import joblib
        data = joblib.load(Path(path))
        self._model = data["model"]
        self._scaler = data["scaler"]
        self._fitted = data["fitted"]
        return self
