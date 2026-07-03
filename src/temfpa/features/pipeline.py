"""Feature pipeline that assembles all features into a flat vector."""

from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from temfpa.features.head_to_head import get_h2h_stats
from temfpa.features.player_availability import get_team_absence_penalty
from temfpa.features.team_form import get_team_form, get_team_home_away_form

NEUTRAL = 0.5
NEUTRAL_GOALS = 1.0


def build_feature_vector(
    db: Session,
    home_team_id: int,
    away_team_id: int,
    season_id: int,
    fixture_date: datetime.date,
) -> dict:
    """Assemble all features into one flat dict.

    All missing / zero-data values default to 0.5 (neutral).
    """
    # Convert datetime to date if needed
    if isinstance(fixture_date, datetime.datetime):
        before_date = fixture_date.date()
    else:
        before_date = fixture_date

    # --- Home team form (last 5 and 10 matches, all venues) ---
    home_form_5 = _safe_form(db, home_team_id, before_date, n=5)
    home_form_10 = _safe_form(db, home_team_id, before_date, n=10)

    # --- Away team form (last 5 and 10 matches, all venues) ---
    away_form_5 = _safe_form(db, away_team_id, before_date, n=5)
    away_form_10 = _safe_form(db, away_team_id, before_date, n=10)

    # --- Home/Away specific form ---
    home_home_form_5 = _safe_home_away_form(db, home_team_id, before_date, is_home=True, n=5)
    away_away_form_5 = _safe_home_away_form(db, away_team_id, before_date, is_home=False, n=5)

    # --- Head-to-head ---
    h2h = _safe_h2h(db, home_team_id, away_team_id, before_date, n=10)

    # --- Absence penalties ---
    home_absence = _safe_absence(db, home_team_id, before_date, before_date)
    away_absence = _safe_absence(db, away_team_id, before_date, before_date)

    return {
        # Home form (all venues)
        "home_win_rate_5": home_form_5.get("win_rate", NEUTRAL),
        "home_win_rate_10": home_form_10.get("win_rate", NEUTRAL),
        "home_goals_scored_5": home_form_5.get("goals_scored_avg", NEUTRAL_GOALS),
        "home_goals_conceded_5": home_form_5.get("goals_conceded_avg", NEUTRAL_GOALS),
        "home_clean_sheet_rate_5": home_form_5.get("clean_sheet_rate", NEUTRAL),
        "home_xg_avg_5": home_form_5.get("xg_avg", NEUTRAL_GOALS),
        "home_xga_avg_5": home_form_5.get("xga_avg", NEUTRAL_GOALS),
        "home_points_per_game_5": home_form_5.get("points_per_game", 1.0),
        # Away form (all venues)
        "away_win_rate_5": away_form_5.get("win_rate", NEUTRAL),
        "away_win_rate_10": away_form_10.get("win_rate", NEUTRAL),
        "away_goals_scored_5": away_form_5.get("goals_scored_avg", NEUTRAL_GOALS),
        "away_goals_conceded_5": away_form_5.get("goals_conceded_avg", NEUTRAL_GOALS),
        "away_clean_sheet_rate_5": away_form_5.get("clean_sheet_rate", NEUTRAL),
        "away_xg_avg_5": away_form_5.get("xg_avg", NEUTRAL_GOALS),
        "away_xga_avg_5": away_form_5.get("xga_avg", NEUTRAL_GOALS),
        "away_points_per_game_5": away_form_5.get("points_per_game", 1.0),
        # Venue-specific form
        "home_home_win_rate_5": home_home_form_5.get("win_rate", NEUTRAL),
        "away_away_win_rate_5": away_away_form_5.get("win_rate", NEUTRAL),
        # Head-to-head
        "h2h_home_win_rate": h2h.get("home_win_rate", NEUTRAL),
        "h2h_draw_rate": h2h.get("draw_rate", 0.25),
        "h2h_away_win_rate": h2h.get("away_win_rate", NEUTRAL),
        "h2h_total": h2h.get("total_matches", 0),
        # Absences
        "home_absence_penalty": home_absence,
        "away_absence_penalty": away_absence,
    }


def _safe_form(db: Session, team_id: int, before_date: datetime.date, n: int) -> dict:
    try:
        from temfpa.features.team_form import get_team_form
        return get_team_form(db, team_id, before_date, n_matches=n)
    except Exception:
        return {}


def _safe_home_away_form(
    db: Session,
    team_id: int,
    before_date: datetime.date,
    is_home: bool,
    n: int,
) -> dict:
    try:
        from temfpa.features.team_form import get_team_home_away_form
        return get_team_home_away_form(db, team_id, before_date, is_home=is_home, n=n)
    except Exception:
        return {}


def _safe_h2h(
    db: Session,
    home_team_id: int,
    away_team_id: int,
    before_date: datetime.date,
    n: int,
) -> dict:
    try:
        return get_h2h_stats(db, home_team_id, away_team_id, before_date, n=n)
    except Exception:
        return {}


def _safe_absence(
    db: Session,
    team_id: int,
    fixture_date: datetime.date,
    before_date: datetime.date,
) -> float:
    try:
        return get_team_absence_penalty(db, team_id, fixture_date, before_date)
    except Exception:
        return 0.0
