"""Scoreline probability computation using Poisson distribution."""

from __future__ import annotations

import scipy.stats


def top_k_scorelines(
    lambda_home: float,
    lambda_away: float,
    k: int = 3,
    max_goals: int = 8,
) -> list[dict]:
    """Return top-k most probable scorelines using bivariate Poisson model.

    Args:
        lambda_home: Expected home goals (Poisson lambda).
        lambda_away: Expected away goals (Poisson lambda).
        k: Number of scorelines to return.
        max_goals: Maximum goals per team to consider.

    Returns:
        List of dicts sorted descending by probability:
        [{"score": "2-1", "homeGoals": 2, "awayGoals": 1, "probability": 0.19}]
    """
    scorelines = []
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            prob = float(
                scipy.stats.poisson.pmf(h, lambda_home)
                * scipy.stats.poisson.pmf(a, lambda_away)
            )
            scorelines.append(
                {
                    "score": f"{h}-{a}",
                    "homeGoals": h,
                    "awayGoals": a,
                    "probability": prob,
                }
            )

    scorelines.sort(key=lambda x: x["probability"], reverse=True)
    return scorelines[:k]


def most_likely_score(lambda_home: float, lambda_away: float) -> str:
    """Return the most likely scoreline as a string like '2-1'."""
    result = top_k_scorelines(lambda_home, lambda_away, k=1)
    return result[0]["score"]
