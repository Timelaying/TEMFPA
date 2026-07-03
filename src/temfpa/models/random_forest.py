"""Random forest predictor for match outcome classification."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier


class RandomForestPredictor:
    """Random forest classifier for match outcome (0=home, 1=draw, 2=away)."""

    def __init__(self) -> None:
        self._model = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            random_state=42,
            n_jobs=-1,
        )
        self._fitted = False

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "RandomForestPredictor":
        """Fit the model. y in {0=home, 1=draw, 2=away}."""
        self._model.fit(X.values.astype(float), y)
        self._fitted = True
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return shape (N, 3) probability array."""
        if not self._fitted:
            n = len(X)
            return np.full((n, 3), 1.0 / 3.0)
        return self._model.predict_proba(X.values.astype(float))

    def save(self, path: Path) -> None:
        """Save model to disk using joblib."""
        import joblib
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"model": self._model, "fitted": self._fitted}, path)

    def load(self, path: Path) -> "RandomForestPredictor":
        """Load model from disk."""
        import joblib
        data = joblib.load(Path(path))
        self._model = data["model"]
        self._fitted = data["fitted"]
        return self
