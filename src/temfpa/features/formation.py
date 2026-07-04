"""Formation-based feature computation."""

from __future__ import annotations

import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from temfpa.db.models import Fixture, Lineup, MatchResult


def get_formation_win_rate(
    db: Session,
    team_id: int,
    formation: str,
    before_date: datetime.date,
    n: int = 20,
) -> dict:
    """Compute team win rate when using a specific formation.

    Returns:
        win_rate, draw_rate, loss_rate, goals_scored_avg, goals_conceded_avg, matches
    """
    before_dt = datetime.datetime.combine(before_date, datetime.time.max)

    rows = (
        db.query(Fixture, MatchResult)
        .join(MatchResult, MatchResult.fixture_id == Fixture.id)
        .join(
            Lineup,
            and_(
                Lineup.fixture_id == Fixture.id,
                Lineup.team_id == team_id,
                Lineup.formation == formation,
            ),
        )
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
        .limit(n)
        .all()
    )

    n_matches = len(rows)
    if n_matches == 0:
        return {
            "win_rate": 0.5,
            "draw_rate": 0.25,
            "loss_rate": 0.25,
            "goals_scored_avg": 1.0,
            "goals_conceded_avg": 1.0,
            "matches": 0,
        }

    wins = draws = losses = 0
    goals_scored = goals_conceded = 0.0

    for fixture, result in rows:
        is_home = fixture.home_team_id == team_id
        scored = (result.home_goals if is_home else result.away_goals) or 0
        conceded = (result.away_goals if is_home else result.home_goals) or 0
        goals_scored += scored
        goals_conceded += conceded

        winner = result.winner
        if winner == "draw":
            draws += 1
        elif (is_home and winner == "home") or (not is_home and winner == "away"):
            wins += 1
        else:
            losses += 1

    return {
        "win_rate": wins / n_matches,
        "draw_rate": draws / n_matches,
        "loss_rate": losses / n_matches,
        "goals_scored_avg": goals_scored / n_matches,
        "goals_conceded_avg": goals_conceded / n_matches,
        "matches": n_matches,
    }


def get_formation_matchup(
    db: Session,
    home_team_id: int,
    home_formation: str,
    away_team_id: int,
    away_formation: str,
    before_date: datetime.date,
) -> dict:
    """Compute historical outcomes when home team used home_formation vs away team used away_formation.

    Returns:
        home_win_rate, draw_rate, away_win_rate
    """
    before_dt = datetime.datetime.combine(before_date, datetime.time.max)

    # Find fixtures where both teams played each other with the specified formations
    home_lineups = db.query(Lineup.fixture_id).filter(
        Lineup.team_id == home_team_id,
        Lineup.formation == home_formation,
    ).subquery()

    away_lineups = db.query(Lineup.fixture_id).filter(
        Lineup.team_id == away_team_id,
        Lineup.formation == away_formation,
    ).subquery()

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
            Fixture.id.in_(home_lineups),
            Fixture.id.in_(away_lineups),
        )
        .all()
    )

    total = len(rows)
    if total == 0:
        return {
            "home_win_rate": 0.5,
            "draw_rate": 0.25,
            "away_win_rate": 0.25,
        }

    home_wins = draws = away_wins = 0

    for fixture, result in rows:
        if fixture.home_team_id == home_team_id:
            # Normal orientation
            if result.winner == "draw":
                draws += 1
            elif result.winner == "home":
                home_wins += 1
            else:
                away_wins += 1
        else:
            # Reversed: home_team_id was the away side
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
    }
