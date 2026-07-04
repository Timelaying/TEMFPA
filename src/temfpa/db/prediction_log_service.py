"""Service functions for the PredictionLog table.

log_prediction      — called from the upcoming endpoint after each prediction
resolve_predictions — called from sync_results after committing results
"""
from __future__ import annotations

import datetime
import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from temfpa.db.models import Fixture, MatchResult, PredictionLog

logger = logging.getLogger(__name__)


def log_prediction(
    db: Session,
    *,
    matchup: dict,
    prediction: dict,
    source: str = "upcoming",
) -> None:
    """Upsert a prediction into PredictionLog.

    matchup    — dict built by _get_upcoming_from_db / _get_showcase
    prediction — dict returned by _run_prediction
    source     — "upcoming" | "manual"
    """
    home_team_id = matchup["homeTeamId"]
    away_team_id = matchup["awayTeamId"]
    fixture_date = datetime.date.fromisoformat(matchup["fixtureDate"][:10])
    league_code = matchup["leagueCode"]

    existing = (
        db.query(PredictionLog)
        .filter_by(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            fixture_date=fixture_date,
            source=source,
        )
        .first()
    )

    if existing:
        # Update to latest model output (prediction may be re-run)
        existing.predicted_result = prediction["resultKey"]
        existing.predicted_confidence = prediction["confidence"]
        existing.home_win_prob = prediction.get("homeWinProbability")
        existing.draw_prob = prediction.get("drawProbability")
        existing.away_win_prob = prediction.get("awayWinProbability")
        existing.likely_score = prediction.get("likelyScore")
    else:
        # Try to link to a real fixture row
        fixture = (
            db.query(Fixture)
            .filter(
                Fixture.home_team_id == home_team_id,
                Fixture.away_team_id == away_team_id,
                Fixture.fixture_date >= datetime.datetime.combine(
                    fixture_date - datetime.timedelta(days=1), datetime.time.min
                ),
                Fixture.fixture_date <= datetime.datetime.combine(
                    fixture_date + datetime.timedelta(days=1), datetime.time.max
                ),
            )
            .first()
        )

        db.add(
            PredictionLog(
                fixture_id=fixture.id if fixture else None,
                league_code=league_code,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                fixture_date=fixture_date,
                predicted_result=prediction["resultKey"],
                predicted_confidence=prediction["confidence"],
                home_win_prob=prediction.get("homeWinProbability"),
                draw_prob=prediction.get("drawProbability"),
                away_win_prob=prediction.get("awayWinProbability"),
                likely_score=prediction.get("likelyScore"),
                source=source,
            )
        )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.debug(
            "Duplicate PredictionLog skipped for %s %s vs %s on %s",
            league_code, home_team_id, away_team_id, fixture_date,
        )


def resolve_predictions(db: Session) -> int:
    """For every unresolved PredictionLog whose fixture is now FINISHED,
    fill in actual_result and is_correct. Returns count resolved."""

    unresolved = (
        db.query(PredictionLog)
        .filter(PredictionLog.is_correct.is_(None))
        .all()
    )

    resolved_count = 0
    for log in unresolved:
        # Find the fixture — by FK first, then by team+date match
        fixture = None
        if log.fixture_id:
            fixture = db.query(Fixture).filter_by(id=log.fixture_id).first()
        if fixture is None:
            fixture = (
                db.query(Fixture)
                .filter(
                    Fixture.home_team_id == log.home_team_id,
                    Fixture.away_team_id == log.away_team_id,
                    Fixture.fixture_date >= datetime.datetime.combine(
                        log.fixture_date - datetime.timedelta(days=1), datetime.time.min
                    ),
                    Fixture.fixture_date <= datetime.datetime.combine(
                        log.fixture_date + datetime.timedelta(days=1), datetime.time.max
                    ),
                )
                .first()
            )

        if not fixture or fixture.status != "FINISHED":
            continue

        result = db.query(MatchResult).filter_by(fixture_id=fixture.id).first()
        if not result or result.winner is None:
            continue

        log.actual_result = result.winner
        log.actual_home_goals = result.home_goals
        log.actual_away_goals = result.away_goals
        log.is_correct = log.predicted_result == result.winner
        log.resolved_at = datetime.datetime.utcnow()

        # Backfill FK if we found the fixture by team+date
        if log.fixture_id is None:
            log.fixture_id = fixture.id

        resolved_count += 1

    db.commit()
    logger.info("resolve_predictions: resolved %d prediction log(s)", resolved_count)
    return resolved_count
