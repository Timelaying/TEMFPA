"""Smoke tests for EloRating — catches import and logic regressions."""
import pytest
from temfpa.models.elo import EloRating, PRIOR_RATINGS, HOME_ADVANTAGE_BY_LEAGUE


def test_elo_imports_cleanly():
    """EloRating must be importable without NameError (guards against missing imports)."""
    elo = EloRating()
    assert elo is not None


def test_build_from_db_uses_datetime(tmp_path):
    """build_from_db must not raise NameError for datetime — regression guard."""
    from unittest.mock import MagicMock, patch

    mock_db = MagicMock()
    # Return empty team list and empty fixture rows
    mock_db.query.return_value.all.return_value = []
    mock_db.query.return_value.join.return_value.filter.return_value.order_by.return_value.all.return_value = []

    # Must not raise NameError / UnboundLocalError
    elo = EloRating.build_from_db(mock_db)
    assert isinstance(elo, EloRating)


def test_prior_ratings_differentiate_teams():
    """Strong teams must have meaningfully higher Elo than weak teams."""
    assert PRIOR_RATINGS["France"] > PRIOR_RATINGS["Haiti"]
    assert PRIOR_RATINGS["Brazil"] > PRIOR_RATINGS["Panama"]
    assert PRIOR_RATINGS["Real Madrid"] > PRIOR_RATINGS["Southampton"]


def test_expected_home_win_prob_strong_vs_weak():
    """A much stronger team should have >70% win probability."""
    elo = EloRating()
    # Manually assign ratings
    elo._ratings = {1: 2040, 2: 1460}  # France-level vs weak side
    h, d, a = elo.expected_home_win_prob(1, 2)
    assert h > 0.70, f"Expected strong home win prob, got H={h:.2f}"
    assert h + d + a == pytest.approx(1.0, abs=1e-6)


def test_per_league_home_advantage():
    """La Liga home advantage must exceed EPL; World Cup must be zero."""
    assert HOME_ADVANTAGE_BY_LEAGUE["LA_LIGA"] > HOME_ADVANTAGE_BY_LEAGUE["EPL"]
    assert HOME_ADVANTAGE_BY_LEAGUE["WORLD_CUP"] == 0.0


def test_neutral_venue_equalises_identical_teams():
    """With identical ratings and no home advantage, probs should be symmetric."""
    elo = EloRating()
    elo._ratings = {1: 1600, 2: 1600}
    h, d, a = elo.expected_home_win_prob(1, 2, league_code="WORLD_CUP")
    assert abs(h - a) < 1e-6, f"Expected symmetry, got H={h:.3f} A={a:.3f}"


def test_fallback_not_all_draws():
    """The dead fallback (0.35/0.30/0.35) must not be returned for known strong teams."""
    elo = EloRating()
    # France (2040) vs Haiti (1460) using prior ratings
    france_id, haiti_id = 999, 998
    elo._names = {france_id: "France", haiti_id: "Haiti"}
    h, d, a = elo.expected_home_win_prob(france_id, haiti_id)
    assert h > 0.60, f"France should dominate Haiti, got H={h:.2f}"
    assert not (abs(h - 0.35) < 0.01 and abs(a - 0.35) < 0.01), \
        "Got dead fallback values — Elo is broken"
