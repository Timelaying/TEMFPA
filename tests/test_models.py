"""Tests for Phase 4: Model Pipeline."""

from __future__ import annotations


import numpy as np
import pandas as pd
import pytest

from temfpa.models.elo import EloRating
from temfpa.models.ensemble import EnsemblePredictor
from temfpa.models.evaluation import evaluate_classifier, evaluate_goals
from temfpa.models.logistic import LogisticPredictor
from temfpa.models.poisson import PoissonGoalModel
from temfpa.models.random_forest import RandomForestPredictor
from temfpa.models.scoreline import top_k_scorelines
from temfpa.models.xgboost_model import XGBoostPredictor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_synthetic_X(n=50, seed=42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "home_win_rate_5": rng.uniform(0, 1, n),
            "home_win_rate_10": rng.uniform(0, 1, n),
            "home_goals_scored_5": rng.uniform(0, 4, n),
            "home_goals_conceded_5": rng.uniform(0, 3, n),
            "away_win_rate_5": rng.uniform(0, 1, n),
            "away_win_rate_10": rng.uniform(0, 1, n),
            "away_goals_scored_5": rng.uniform(0, 4, n),
            "away_goals_conceded_5": rng.uniform(0, 3, n),
        }
    )


def make_synthetic_y(n=50, seed=42) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(rng.integers(0, 3, n))


# ---------------------------------------------------------------------------
# ELO tests
# ---------------------------------------------------------------------------


def test_elo_updates_ratings():
    """Feed 3 results, assert winner gains rating."""
    elo = EloRating(k=30, base_rating=1500)
    elo.update(1, 2, "home")
    elo.update(1, 3, "home")
    elo.update(2, 3, "home")
    # Team 1 won twice, should be above base
    assert elo.get_rating(1) > 1500
    # Team 3 lost twice, should be below base
    assert elo.get_rating(3) < 1500


def test_elo_expected_probs_sum_to_one():
    """Assert home+draw+away = 1.0."""
    elo = EloRating(k=30, base_rating=1500)
    elo.update(1, 2, "home")
    elo.update(2, 3, "draw")
    h, d, a = elo.expected_home_win_prob(1, 2)
    assert h + d + a == pytest.approx(1.0, abs=1e-9)
    assert h >= 0
    assert d >= 0
    assert a >= 0


# ---------------------------------------------------------------------------
# Poisson tests
# ---------------------------------------------------------------------------


def test_poisson_predict_reasonable():
    """Fit on synthetic data, assert lambda in [0.1, 6]."""
    X = make_synthetic_X(n=50)
    home_goals = pd.Series(np.random.randint(0, 4, 50).astype(float))
    away_goals = pd.Series(np.random.randint(0, 3, 50).astype(float))
    model = PoissonGoalModel()
    model.fit(X, home_goals, away_goals)
    lh, la = model.predict(X.iloc[:1])
    assert 0.1 <= lh <= 6.0
    assert 0.1 <= la <= 6.0


# ---------------------------------------------------------------------------
# Scoreline tests
# ---------------------------------------------------------------------------


def test_scoreline_probabilities_sum_reasonable():
    """Assert top-3 probs sum < 1.0 and all > 0."""
    results = top_k_scorelines(1.5, 1.2, k=3)
    probs = [r["probability"] for r in results]
    assert all(p > 0 for p in probs)
    assert sum(probs) < 1.0


def test_scoreline_returns_k_results():
    """Assert len == k."""
    results = top_k_scorelines(1.5, 1.2, k=3)
    assert len(results) == 3

    results5 = top_k_scorelines(2.0, 1.0, k=5)
    assert len(results5) == 5


def test_scoreline_structure():
    """Assert correct keys and types."""
    results = top_k_scorelines(1.5, 1.2, k=3)
    for r in results:
        assert "score" in r
        assert "homeGoals" in r
        assert "awayGoals" in r
        assert "probability" in r
        assert isinstance(r["score"], str)
        assert "-" in r["score"]


# ---------------------------------------------------------------------------
# Logistic tests
# ---------------------------------------------------------------------------


def test_logistic_fit_predict():
    """Fit on 50 synthetic samples, predict_proba shape (N,3)."""
    X = make_synthetic_X(n=50)
    y = make_synthetic_y(n=50)
    model = LogisticPredictor()
    model.fit(X, y)
    proba = model.predict_proba(X[:10])
    assert proba.shape == (10, 3)
    # Probabilities sum to 1
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-6)


# ---------------------------------------------------------------------------
# Random Forest tests
# ---------------------------------------------------------------------------


def test_random_forest_fit_predict():
    """Fit on 50 synthetic samples, predict_proba shape (N,3)."""
    X = make_synthetic_X(n=50)
    y = make_synthetic_y(n=50)
    model = RandomForestPredictor()
    model.fit(X, y)
    proba = model.predict_proba(X[:10])
    assert proba.shape == (10, 3)
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-6)


# ---------------------------------------------------------------------------
# XGBoost tests
# ---------------------------------------------------------------------------


def test_xgboost_fit_predict():
    """Fit on 50 synthetic samples, predict_proba shape (N,3)."""
    X = make_synthetic_X(n=50)
    y = make_synthetic_y(n=50)
    model = XGBoostPredictor()
    model.fit(X, y)
    proba = model.predict_proba(X[:10])
    assert proba.shape == (10, 3)
    np.testing.assert_allclose(proba.sum(axis=1), 1.0, atol=1e-5)


# ---------------------------------------------------------------------------
# Ensemble tests
# ---------------------------------------------------------------------------


class _StubModel:
    """Stub model that returns fixed probabilities."""

    def __init__(self, proba: np.ndarray) -> None:
        self._proba = proba

    def predict_proba(self, X):
        n = len(X)
        return np.tile(self._proba, (n, 1))


def test_ensemble_weighted_average():
    """Two models with known probas, assert weighted output."""
    proba_a = np.array([0.6, 0.2, 0.2])
    proba_b = np.array([0.2, 0.4, 0.4])

    model_a = _StubModel(proba_a)
    model_b = _StubModel(proba_b)

    # Equal weights → average
    ensemble = EnsemblePredictor(models=[model_a, model_b], weights=[1.0, 1.0])
    X = pd.DataFrame({"a": [1]})
    result = ensemble.predict_proba(X)
    expected = (proba_a + proba_b) / 2.0
    np.testing.assert_allclose(result[0], expected, atol=1e-9)


def test_ensemble_confidence_high():
    """Assert 'High' when max_prob > 0.55."""
    proba = np.array([0.65, 0.20, 0.15])
    model = _StubModel(proba)
    ensemble = EnsemblePredictor(models=[model])
    X = pd.DataFrame({"a": [1]})
    _, confidence, _ = ensemble.predict_outcome(X)
    assert confidence == "High"


def test_ensemble_confidence_low():
    """Assert 'Low' when max_prob < 0.42."""
    proba = np.array([0.38, 0.32, 0.30])
    model = _StubModel(proba)
    ensemble = EnsemblePredictor(models=[model])
    X = pd.DataFrame({"a": [1]})
    _, confidence, _ = ensemble.predict_outcome(X)
    assert confidence == "Low"


# ---------------------------------------------------------------------------
# Evaluation tests
# ---------------------------------------------------------------------------


def test_evaluate_classifier_keys():
    """Assert all metric keys present."""
    y_true = [0, 1, 2, 0, 1]
    y_pred = [0, 2, 1, 0, 1]
    y_proba = np.array([
        [0.7, 0.2, 0.1],
        [0.1, 0.3, 0.6],
        [0.2, 0.6, 0.2],
        [0.8, 0.1, 0.1],
        [0.1, 0.7, 0.2],
    ])
    metrics = evaluate_classifier(y_true, y_pred, y_proba)
    required_keys = {"accuracy", "precision_macro", "recall_macro", "f1_macro", "log_loss", "confusion_matrix"}
    assert required_keys.issubset(set(metrics.keys()))
    assert isinstance(metrics["confusion_matrix"], list)
    assert len(metrics["confusion_matrix"]) == 3


def test_evaluate_goals_mae():
    """Assert exact MAE on synthetic data."""
    y_true_home = np.array([2.0, 1.0, 3.0])
    y_true_away = np.array([1.0, 0.0, 2.0])
    pred_home = np.array([1.5, 1.5, 2.5])
    pred_away = np.array([0.5, 0.5, 1.5])

    metrics = evaluate_goals(y_true_home, y_true_away, pred_home, pred_away)
    assert "mae_home" in metrics
    assert "mae_away" in metrics
    assert "mae_total" in metrics
    assert "exact_score_accuracy" in metrics

    # MAE home = mean(|2-1.5|, |1-1.5|, |3-2.5|) = mean(0.5, 0.5, 0.5) = 0.5
    assert metrics["mae_home"] == pytest.approx(0.5)
    assert metrics["mae_away"] == pytest.approx(0.5)
    assert metrics["mae_total"] == pytest.approx(0.5)
