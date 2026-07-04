"""Team form feature computation."""

from __future__ import annotations

import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from temfpa.db.models import Fixture, MatchResult


def get_team_form(
    db: Session,
    team_id: int,
    before_date: datetime.date,
    n_matches: int = 5,
) -> dict:
    """Compute rolling team form features for the last n_matches before before_date.

    Returns a dict with:
        win_rate, draw_rate, loss_rate, goals_scored_avg, goals_conceded_avg,
        xg_avg, xga_avg, clean_sheet_rate, points_per_game
    """
    # Convert date to datetime for comparison
    before_dt = datetime.datetime.combine(before_date, datetime.time.max)

    rows = (
        db.query(Fixture, MatchResult)
        .join(MatchResult, MatchResult.fixture_id == Fixture.id)
        .filter(
            or_(
                Fixture.home_team_id == team_id,
                Fixture.away_team_id == team_id,
            ),
            Fixture.fixture_date < before_dt,
            Fixture.status == "FINISHED",
            MatchResult.winner.isnot(None),
        )
        .order_by(Fixture.fixture_date.desc())
        .limit(n_matches)
        .all()
    )

    return _compute_form_stats(rows, team_id)


def get_team_home_away_form(
    db: Session,
    team_id: int,
    before_date: datetime.date,
    is_home: bool,
    n: int = 5,
) -> dict:
    """Compute team form filtered to home-only or away-only fixtures."""
    before_dt = datetime.datetime.combine(before_date, datetime.time.max)

    if is_home:
        team_filter = Fixture.home_team_id == team_id
    else:
        team_filter = Fixture.away_team_id == team_id

    rows = (
        db.query(Fixture, MatchResult)
        .join(MatchResult, MatchResult.fixture_id == Fixture.id)
        .filter(
            team_filter,
            Fixture.fixture_date < before_dt,
            Fixture.status == "FINISHED",
            MatchResult.winner.isnot(None),
        )
        .order_by(Fixture.fixture_date.desc())
        .limit(n)
        .all()
    )

    return _compute_form_stats(rows, team_id)


def _compute_form_stats(rows: list, team_id: int) -> dict:
    """Compute form statistics from a list of (Fixture, MatchResult) tuples."""
    if not rows:
        return {
            "win_rate": 0.5,
            "draw_rate": 0.25,
            "loss_rate": 0.25,
            "goals_scored_avg": 1.0,
            "goals_conceded_avg": 1.0,
            "xg_avg": 1.0,
            "xga_avg": 1.0,
            "clean_sheet_rate": 0.25,
            "points_per_game": 1.0,
        }

    wins = draws = losses = 0
    goals_scored = goals_conceded = 0.0
    xg_total = xga_total = 0.0
    xg_count = 0
    clean_sheets = 0
    n = len(rows)

    for fixture, result in rows:
        is_home = fixture.home_team_id == team_id

        if is_home:
            scored = result.home_goals or 0
            conceded = result.away_goals or 0
            xg = result.home_xg
            xga = result.away_xg
            winner = result.winner
        else:
            scored = result.away_goals or 0
            conceded = result.home_goals or 0
            xg = result.away_xg
            xga = result.home_xg
            winner = result.winner

        goals_scored += scored
        goals_conceded += conceded

        if conceded == 0:
            clean_sheets += 1

        if xg is not None and xga is not None:
            xg_total += xg
            xga_total += xga
            xg_count += 1

        if winner == "draw":
            draws += 1
        elif (is_home and winner == "home") or (not is_home and winner == "away"):
            wins += 1
        else:
            losses += 1

    xg_avg = (xg_total / xg_count) if xg_count > 0 else goals_scored / n
    xga_avg = (xga_total / xg_count) if xg_count > 0 else goals_conceded / n

    return {
        "win_rate": wins / n,
        "draw_rate": draws / n,
        "loss_rate": losses / n,
        "goals_scored_avg": goals_scored / n,
        "goals_conceded_avg": goals_conceded / n,
        "xg_avg": xg_avg,
        "xga_avg": xga_avg,
        "clean_sheet_rate": clean_sheets / n,
        "points_per_game": (wins * 3 + draws) / n,
    }
