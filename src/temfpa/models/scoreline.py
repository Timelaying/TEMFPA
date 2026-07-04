"""Scoreline probability computation using Dixon-Coles corrected Poisson.

Dixon-Coles correction adjusts the probabilities of low-scoring outcomes
(0-0, 1-0, 0-1, 1-1) which vanilla Poisson systematically mis-estimates.
"""

from __future__ import annotations

import scipy.stats

# Correlation parameter ρ — negative value means 0-0 and 1-1 are slightly
# less likely than pure Poisson predicts, correcting for the fact that
# football goals are not fully independent events.
_RHO = -0.13


def _dixon_coles_tau(h: int, a: int, lh: float, la: float, rho: float) -> float:
    """Dixon-Coles low-score correction factor τ(i,j,λh,λa,ρ).

    Only applied when max(h, a) <= 1; returns 1.0 otherwise.
    """
    if h == 0 and a == 0:
        return 1.0 - lh * la * rho
    if h == 1 and a == 0:
        return 1.0 + la * rho
    if h == 0 and a == 1:
        return 1.0 + lh * rho
    if h == 1 and a == 1:
        return 1.0 - rho
    return 1.0


def top_k_scorelines(
    lambda_home: float,
    lambda_away: float,
    k: int = 3,
    max_goals: int = 8,
    rho: float = _RHO,
) -> list[dict]:
    """Return top-k most probable scorelines using Dixon-Coles corrected Poisson.

    Args:
        lambda_home: Expected home goals.
        lambda_away: Expected away goals.
        k: Number of scorelines to return.
        max_goals: Maximum goals per team to consider.
        rho: Dixon-Coles correlation parameter (default −0.13).

    Returns:
        List of dicts sorted descending by probability:
        [{"score": "2-1", "homeGoals": 2, "awayGoals": 1, "probability": 0.19}]
    """
    scorelines = []
    total = 0.0
    for h in range(max_goals + 1):
        for a in range(max_goals + 1):
            raw = float(
                scipy.stats.poisson.pmf(h, lambda_home)
                * scipy.stats.poisson.pmf(a, lambda_away)
            )
            tau = _dixon_coles_tau(h, a, lambda_home, lambda_away, rho)
            prob = raw * tau
            scorelines.append({"score": f"{h}-{a}", "homeGoals": h, "awayGoals": a, "probability": prob})
            total += prob

    # Re-normalise so probabilities sum to 1 over the grid
    if total > 0:
        for s in scorelines:
            s["probability"] /= total

    scorelines.sort(key=lambda x: x["probability"], reverse=True)
    return scorelines[:k]


def most_likely_score(lambda_home: float, lambda_away: float) -> str:
    """Return the most likely scoreline as a string like '2-1'."""
    result = top_k_scorelines(lambda_home, lambda_away, k=1)
    return result[0]["score"]
