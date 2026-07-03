"""Player availability and impact feature computation."""

from __future__ import annotations

import datetime

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from temfpa.db.models import (
    Fixture,
    InjuryOrAbsence,
    Lineup,
    LineupPlayer,
    MatchResult,
)


def get_player_impact(
    db: Session,
    player_id: int,
    team_id: int,
    before_date: datetime.date,
    n: int = 20,
) -> dict:
    """Compute the impact of a player on team results.

    Splits the last n team matches into:
    - matches WHERE the player appeared in the lineup
    - matches WHERE the player did NOT appear in the lineup

    Returns:
        win_pct_with, draw_pct_with, loss_pct_with,
        goals_scored_with, goals_conceded_with,
        win_pct_without, goals_scored_without, goals_conceded_without,
        impact_score (win_pct_with - win_pct_without)
    """
    before_dt = datetime.datetime.combine(before_date, datetime.time.max)

    # Get last n finished matches for this team
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
        .limit(n)
        .all()
    )

    if not rows:
        return _empty_impact()

    # Find fixture IDs where player appeared
    fixture_ids = [f.id for f, _ in rows]
    lineup_fixture_ids = set(
        row[0]
        for row in db.query(Lineup.fixture_id)
        .join(LineupPlayer, LineupPlayer.lineup_id == Lineup.id)
        .filter(
            Lineup.team_id == team_id,
            Lineup.fixture_id.in_(fixture_ids),
            LineupPlayer.player_id == player_id,
        )
        .all()
    )

    with_stats = _collect_stats(rows, team_id, lineup_fixture_ids, in_group=True)
    without_stats = _collect_stats(rows, team_id, lineup_fixture_ids, in_group=False)

    win_pct_with = with_stats["win_rate"]
    win_pct_without = without_stats["win_rate"]

    return {
        "win_pct_with": win_pct_with,
        "draw_pct_with": with_stats["draw_rate"],
        "loss_pct_with": with_stats["loss_rate"],
        "goals_scored_with": with_stats["goals_scored_avg"],
        "goals_conceded_with": with_stats["goals_conceded_avg"],
        "win_pct_without": win_pct_without,
        "goals_scored_without": without_stats["goals_scored_avg"],
        "goals_conceded_without": without_stats["goals_conceded_avg"],
        "impact_score": win_pct_with - win_pct_without,
    }


def get_team_absence_penalty(
    db: Session,
    team_id: int,
    fixture_date: datetime.date,
    before_date: datetime.date,
) -> float:
    """Sum impact_scores for all players confirmed absent for the fixture.

    An absence is active if:
    - end_date is None (ongoing) OR end_date >= fixture_date
    - start_date is None OR start_date <= fixture_date
    """
    absences = (
        db.query(InjuryOrAbsence)
        .filter(
            InjuryOrAbsence.team_id == team_id,
            or_(
                InjuryOrAbsence.end_date.is_(None),
                InjuryOrAbsence.end_date >= fixture_date,
            ),
            or_(
                InjuryOrAbsence.start_date.is_(None),
                InjuryOrAbsence.start_date <= fixture_date,
            ),
        )
        .all()
    )

    total_penalty = 0.0
    for absence in absences:
        impact = get_player_impact(
            db,
            player_id=absence.player_id,
            team_id=team_id,
            before_date=before_date,
            n=20,
        )
        score = impact.get("impact_score", 0.0)
        if score > 0:
            total_penalty += score

    return total_penalty


def _collect_stats(
    rows: list,
    team_id: int,
    player_fixture_ids: set,
    in_group: bool,
) -> dict:
    """Compute aggregate stats for fixtures where player was (or was not) present."""
    subset = [
        (f, r)
        for f, r in rows
        if (f.id in player_fixture_ids) == in_group
    ]

    if not subset:
        return {
            "win_rate": 0.5,
            "draw_rate": 0.25,
            "loss_rate": 0.25,
            "goals_scored_avg": 1.0,
            "goals_conceded_avg": 1.0,
        }

    wins = draws = losses = 0
    goals_scored = goals_conceded = 0.0
    n = len(subset)

    for fixture, result in subset:
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
        "win_rate": wins / n,
        "draw_rate": draws / n,
        "loss_rate": losses / n,
        "goals_scored_avg": goals_scored / n,
        "goals_conceded_avg": goals_conceded / n,
    }


def _empty_impact() -> dict:
    return {
        "win_pct_with": 0.5,
        "draw_pct_with": 0.25,
        "loss_pct_with": 0.25,
        "goals_scored_with": 1.0,
        "goals_conceded_with": 1.0,
        "win_pct_without": 0.5,
        "goals_scored_without": 1.0,
        "goals_conceded_without": 1.0,
        "impact_score": 0.0,
    }
