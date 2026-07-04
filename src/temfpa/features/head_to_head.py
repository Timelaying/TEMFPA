"""Head-to-head statistics feature computation."""

from __future__ import annotations

import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from temfpa.db.models import Fixture, MatchResult


def get_h2h_stats(
    db: Session,
    home_team_id: int,
    away_team_id: int,
    before_date: datetime.date,
    n: int = 10,
) -> dict:
    """Compute head-to-head statistics between two teams.

    Returns:
        home_win_rate: fraction of matches won by home_team_id (regardless of venue)
        draw_rate: fraction of draws
        away_win_rate: fraction of matches won by away_team_id (regardless of venue)
        avg_home_goals: avg goals scored by home_team_id across all h2h matches
        avg_away_goals: avg goals scored by away_team_id across all h2h matches
        total_matches: total number of h2h matches (used as confidence weight)
    """
    before_dt = datetime.datetime.combine(before_date, datetime.time.max)

    rows = (
        db.query(Fixture, MatchResult)
        .join(MatchResult, MatchResult.fixture_id == Fixture.id)
        .filter(
            or_(
                and_(
                    Fixture.home_team_id == home_team_id,
                    Fixture.away_team_id == away_team_id,
                ),
                and_(
                    Fixture.home_team_id == away_team_id,
                    Fixture.away_team_id == home_team_id,
                ),
            ),
            Fixture.fixture_date < before_dt,
            Fixture.status == "FINISHED",
            MatchResult.winner.isnot(None),
        )
        .order_by(Fixture.fixture_date.desc())
        .limit(n)
        .all()
    )

    total = len(rows)
    if total == 0:
        return {
            "home_win_rate": 0.5,
            "draw_rate": 0.25,
            "away_win_rate": 0.25,
            "avg_home_goals": 1.0,
            "avg_away_goals": 1.0,
            "total_matches": 0,
        }

    home_wins = draws = away_wins = 0
    home_goals_total = away_goals_total = 0.0

    for fixture, result in rows:
        # Determine perspective: who is "home_team_id" in each match?
        if fixture.home_team_id == home_team_id:
            # Normal orientation
            home_goals_total += result.home_goals or 0
            away_goals_total += result.away_goals or 0
            if result.winner == "draw":
                draws += 1
            elif result.winner == "home":
                home_wins += 1
            else:
                away_wins += 1
        else:
            # Reversed orientation — home_team_id was the away team
            home_goals_total += result.away_goals or 0
            away_goals_total += result.home_goals or 0
            if result.winner == "draw":
                draws += 1
            elif result.winner == "away":
                home_wins += 1
            else:
                away_wins += 1

    return {
        "home_win_rate": home_wins / total,
        "draw_rate": draws / total,
        "away_win_rate": away_wins / total,
        "avg_home_goals": home_goals_total / total,
        "avg_away_goals": away_goals_total / total,
        "total_matches": total,
    }
