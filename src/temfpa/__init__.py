"""TEMFPA package."""

from temfpa.analytics import (
    add_match_metrics,
    batch_head_to_head,
    export_results,
    plot_head_to_head_goals,
    predict_match_outcomes,
)
from temfpa.retrieval import get_match_results, get_team_position

__all__ = [
    "get_team_position",
    "get_match_results",
    "add_match_metrics",
    "predict_match_outcomes",
    "batch_head_to_head",
    "export_results",
    "plot_head_to_head_goals",
]
