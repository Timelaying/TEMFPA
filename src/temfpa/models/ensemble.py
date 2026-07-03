"""Ensemble predictor combining multiple models via weighted averaging."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


class EnsemblePredictor:
    """Combines multiple classifiers via weighted probability averaging."""

    OUTCOME_LABELS = {0: "home", 1: "draw", 2: "away"}
    OUTCOME_DISPLAY = {"home": "Home Win", "draw": "Draw", "away": "Away Win"}

    def __init__(
        self,
        models: list,
        weights: Optional[list[float]] = None,
    ) -> None:
        self.models = models
        if weights is None:
            self.weights = [1.0 / len(models)] * len(models)
        else:
            total = sum(weights)
            self.weights = [w / total for w in weights]

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return weighted average probability array of shape (N, 3)."""
        if not self.models:
            n = len(X)
            return np.full((n, 3), 1.0 / 3.0)

        weighted_sum = None
        for model, weight in zip(self.models, self.weights):
            proba = model.predict_proba(X)
            if weighted_sum is None:
                weighted_sum = weight * proba
            else:
                weighted_sum += weight * proba

        return weighted_sum

    def predict_outcome(
        self, X: pd.DataFrame
    ) -> tuple[str, str, dict]:
        """Return (result, confidence, probs).

        result: "home" | "draw" | "away"
        confidence: "High" | "Medium" | "Low"
        probs: {"home": float, "draw": float, "away": float}
        """
        proba = self.predict_proba(X)
        avg_proba = proba.mean(axis=0)

        idx = int(np.argmax(avg_proba))
        result = self.OUTCOME_LABELS[idx]
        max_prob = float(avg_proba[idx])

        if max_prob > 0.55:
            confidence = "High"
        elif max_prob > 0.42:
            confidence = "Medium"
        else:
            confidence = "Low"

        probs = {
            "home": float(avg_proba[0]),
            "draw": float(avg_proba[1]),
            "away": float(avg_proba[2]),
        }
        return result, confidence, probs

    def save(self, path: Path) -> None:
        """Save ensemble config to disk using joblib."""
        import joblib
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({"models": self.models, "weights": self.weights}, path)

    @classmethod
    def load(cls, path: Path) -> "EnsemblePredictor":
        """Load ensemble from disk."""
        import joblib
        data = joblib.load(Path(path))
        return cls(models=data["models"], weights=data["weights"])
