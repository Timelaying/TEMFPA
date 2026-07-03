"""Training pipeline: build training data, time-split, train all models."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from temfpa.features.pipeline import build_feature_vector
from temfpa.models.elo import EloRating
from temfpa.models.ensemble import EnsemblePredictor
from temfpa.models.logistic import LogisticPredictor
from temfpa.models.poisson import PoissonGoalModel
from temfpa.models.random_forest import RandomForestPredictor
from temfpa.models.xgboost_model import XGBoostPredictor


OUTCOME_MAP = {"home": 0, "draw": 1, "away": 2}


def build_training_data(
    db: Session,
    league_id: Optional[int] = None,
    seasons: Optional[list[str]] = None,
) -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """Build training dataset from finished fixtures.

    Returns:
        (X, y_outcome, y_home_goals, y_away_goals)
        X is built from build_feature_vector for each finished fixture.
        y_outcome: 0=home, 1=draw, 2=away.
        Sorted by fixture_date for time-based split.
    """
    from temfpa.db.models import Fixture, MatchResult, Season

    query = (
        db.query(Fixture, MatchResult)
        .join(MatchResult, MatchResult.fixture_id == Fixture.id)
        .filter(
            Fixture.status == "FINISHED",
            MatchResult.winner.isnot(None),
            MatchResult.home_goals.isnot(None),
            MatchResult.away_goals.isnot(None),
        )
    )

    if league_id is not None:
        query = query.join(Season, Season.id == Fixture.season_id).filter(
            Season.league_id == league_id
        )

    if seasons:
        if league_id is None:
            query = query.join(Season, Season.id == Fixture.season_id)
        query = query.filter(Season.label.in_(seasons))

    rows = query.order_by(Fixture.fixture_date.asc()).all()

    records = []
    for fixture, result in rows:
        fixture_date = (
            fixture.fixture_date.date()
            if isinstance(fixture.fixture_date, datetime.datetime)
            else fixture.fixture_date
        )
        try:
            fv = build_feature_vector(
                db,
                home_team_id=fixture.home_team_id,
                away_team_id=fixture.away_team_id,
                season_id=fixture.season_id,
                fixture_date=fixture_date,
            )
        except Exception:
            continue

        outcome = OUTCOME_MAP.get(result.winner, 1)
        records.append(
            {
                **fv,
                "_outcome": outcome,
                "_home_goals": result.home_goals,
                "_away_goals": result.away_goals,
                "_fixture_date": fixture_date,
            }
        )

    if not records:
        empty_X = pd.DataFrame()
        empty_y = pd.Series(dtype=int)
        return empty_X, empty_y, empty_y, empty_y

    df = pd.DataFrame(records).sort_values("_fixture_date")
    feature_cols = [c for c in df.columns if not c.startswith("_")]

    X = df[feature_cols].reset_index(drop=True)
    y_outcome = df["_outcome"].reset_index(drop=True)
    y_home_goals = df["_home_goals"].reset_index(drop=True)
    y_away_goals = df["_away_goals"].reset_index(drop=True)

    return X, y_outcome, y_home_goals, y_away_goals


def time_split(
    X: pd.DataFrame,
    y: pd.Series,
    test_frac: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Chronological train/test split (NOT random).

    Returns (X_train, X_test, y_train, y_test).
    """
    n = len(X)
    split_idx = int(n * (1 - test_frac))
    X_train = X.iloc[:split_idx].reset_index(drop=True)
    X_test = X.iloc[split_idx:].reset_index(drop=True)
    y_train = y.iloc[:split_idx].reset_index(drop=True)
    y_test = y.iloc[split_idx:].reset_index(drop=True)
    return X_train, X_test, y_train, y_test


def train_all(
    db: Session,
    save_dir: Path,
    league_id: Optional[int] = None,
) -> dict:
    """Train all models and save to save_dir.

    Returns dict of trained models:
    {
        "logistic": LogisticPredictor,
        "random_forest": RandomForestPredictor,
        "xgboost": XGBoostPredictor,
        "poisson": PoissonGoalModel,
        "elo": EloRating,
        "ensemble": EnsemblePredictor,
    }
    """
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    X, y_outcome, y_home_goals, y_away_goals = build_training_data(db, league_id=league_id)

    logistic = LogisticPredictor()
    rf = RandomForestPredictor()
    xgb_model = XGBoostPredictor()
    poisson = PoissonGoalModel()

    if len(X) >= 10:
        X_train, X_test, y_train, y_test = time_split(X, y_outcome)
        yh_train, _, ya_train, _ = time_split(X, y_home_goals)

        logistic.fit(X_train, y_train)
        rf.fit(X_train, y_train)
        xgb_model.fit(X_train, y_train)
        poisson.fit(X_train, yh_train, ya_train)
    elif len(X) > 0:
        logistic.fit(X, y_outcome)
        rf.fit(X, y_outcome)
        xgb_model.fit(X, y_outcome)
        poisson.fit(X, y_home_goals, y_away_goals)

    # Build Elo from DB
    elo = EloRating.build_from_db(db, league_id=league_id)

    # Ensemble: logistic + RF + XGB with equal weights
    ensemble = EnsemblePredictor(
        models=[logistic, rf, xgb_model],
        weights=[1.0, 1.0, 1.0],
    )

    # Save all models
    logistic.save(save_dir / "logistic.joblib")
    rf.save(save_dir / "random_forest.joblib")
    xgb_model.save(save_dir / "xgboost.joblib")
    poisson.save(save_dir / "poisson.joblib")
    ensemble.save(save_dir / "ensemble.joblib")

    return {
        "logistic": logistic,
        "random_forest": rf,
        "xgboost": xgb_model,
        "poisson": poisson,
        "elo": elo,
        "ensemble": ensemble,
    }
