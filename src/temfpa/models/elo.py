"""Elo rating system for team strength estimation."""

from __future__ import annotations

import math
from typing import Optional


class EloRating:
    """Elo rating system for football teams."""

    def __init__(self, k: float = 30, base_rating: float = 1500) -> None:
        self.k = k
        self.base_rating = base_rating
        self._ratings: dict[int, float] = {}

    def get_rating(self, team_id: int) -> float:
        """Return current Elo rating for a team (default to base_rating)."""
        return self._ratings.get(team_id, self.base_rating)

    def _expected(self, rating_a: float, rating_b: float) -> float:
        """Expected score for team A given two ratings (logistic formula)."""
        return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))

    def update(self, home_team_id: int, away_team_id: int, result: str) -> None:
        """Update Elo ratings after a match.

        Args:
            home_team_id: ID of the home team.
            away_team_id: ID of the away team.
            result: "home", "away", or "draw".
        """
        home_rating = self.get_rating(home_team_id)
        away_rating = self.get_rating(away_team_id)

        expected_home = self._expected(home_rating, away_rating)
        expected_away = 1.0 - expected_home

        if result == "home":
            actual_home, actual_away = 1.0, 0.0
        elif result == "away":
            actual_home, actual_away = 0.0, 1.0
        else:  # draw
            actual_home, actual_away = 0.5, 0.5

        self._ratings[home_team_id] = home_rating + self.k * (actual_home - expected_home)
        self._ratings[away_team_id] = away_rating + self.k * (actual_away - expected_away)

    def expected_home_win_prob(
        self, home_team_id: int, away_team_id: int
    ) -> tuple[float, float, float]:
        """Return (home_win_prob, draw_prob, away_win_prob) using logistic formula.

        Draw probability is approximated as 0.25 * (1 - |home_win_prob - away_win_prob|),
        clamped to [0, 1]. The remaining probability is split between home and away.
        """
        home_rating = self.get_rating(home_team_id)
        away_rating = self.get_rating(away_team_id)

        raw_home = self._expected(home_rating, away_rating)
        raw_away = 1.0 - raw_home

        # Approximate draw probability
        draw_prob = 0.25 * (1.0 - abs(raw_home - raw_away))
        draw_prob = max(0.0, min(1.0, draw_prob))

        # Distribute remaining probability between home and away
        remaining = 1.0 - draw_prob
        home_win_prob = raw_home * remaining
        away_win_prob = raw_away * remaining

        # Normalize to ensure sum = 1
        total = home_win_prob + draw_prob + away_win_prob
        if total > 0:
            home_win_prob /= total
            draw_prob /= total
            away_win_prob /= total

        return home_win_prob, draw_prob, away_win_prob

    @classmethod
    def build_from_db(
        cls,
        db,
        league_id: Optional[int] = None,
        before_date=None,
        k: float = 30,
        base_rating: float = 1500,
    ) -> "EloRating":
        """Build Elo ratings by replaying all MatchResults chronologically.

        Args:
            db: SQLAlchemy session.
            league_id: Optional filter to a specific league.
            before_date: Optional cutoff date.
            k: K-factor.
            base_rating: Starting rating for all teams.
        """
        from sqlalchemy import and_
        from temfpa.db.models import Fixture, MatchResult, Season

        elo = cls(k=k, base_rating=base_rating)

        query = (
            db.query(Fixture, MatchResult)
            .join(MatchResult, MatchResult.fixture_id == Fixture.id)
            .filter(
                Fixture.status == "FINISHED",
                MatchResult.winner.isnot(None),
            )
        )

        if league_id is not None:
            query = query.join(Season, Season.id == Fixture.season_id).filter(
                Season.league_id == league_id
            )

        if before_date is not None:
            import datetime
            if isinstance(before_date, datetime.date) and not isinstance(before_date, datetime.datetime):
                before_date = datetime.datetime.combine(before_date, datetime.time.max)
            query = query.filter(Fixture.fixture_date < before_date)

        rows = query.order_by(Fixture.fixture_date.asc()).all()

        for fixture, result in rows:
            elo.update(fixture.home_team_id, fixture.away_team_id, result.winner)

        return elo
