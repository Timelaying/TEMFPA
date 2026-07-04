"""Upcoming predictions endpoint — proactively predicts featured matches.

GET /api/v2/upcoming-predictions

Returns a curated set of predictions for notable upcoming matches across all
supported competitions. Queries SCHEDULED fixtures from the DB first; if fewer
than needed are found, fills from a curated showcase list of marquee matchups.
"""

from __future__ import annotations

import datetime
import logging
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from temfpa.api.dependencies import get_db
import time as _time

from temfpa.db.models import Fixture, League, MatchResult, Season, Team
from temfpa.db.prediction_log_service import log_prediction

logger = logging.getLogger(__name__)
router = APIRouter()

_UPCOMING_CACHE: dict = {}
_CACHE_TTL = 1800  # 30 minutes

# ---------------------------------------------------------------------------
# Curated showcase matchups — shown when no scheduled fixtures exist in the DB.
# Covers all 6 leagues including UCL.  Updated to reflect current season
# typical fixtures. Stored as (league_code, home_name, away_name).
# ---------------------------------------------------------------------------

SHOWCASE: list[tuple[str, str, str]] = [
    # UCL — classic heavyweight clashes
    ("UCL",        "Real Madrid",          "Bayern Munich"),
    ("UCL",        "Arsenal",              "Paris Saint-Germain"),
    ("UCL",        "Inter Milan",          "Manchester City"),
    ("UCL",        "Borussia Dortmund",    "Barcelona"),
    # EPL — top-of-table rivalry
    ("EPL",        "Liverpool",            "Manchester City"),
    ("EPL",        "Arsenal",              "Chelsea"),
    # La Liga — El Clásico
    ("LA_LIGA",    "Real Madrid",          "Barcelona"),
    ("LA_LIGA",    "Atletico Madrid",      "Real Madrid"),
    # Bundesliga — Der Klassiker
    ("BUNDESLIGA", "Bayern Munich",        "Borussia Dortmund"),
    ("BUNDESLIGA", "Bayer Leverkusen",     "Bayern Munich"),
    # Serie A — Derby d'Italia + Derby della Madonnina
    ("SERIE_A",    "Inter Milan",          "Juventus"),
    ("SERIE_A",    "AC Milan",             "Inter Milan"),
    # Ligue 1 — PSG vs everyone
    ("LIGUE_1",    "Paris Saint-Germain",  "Monaco"),
    ("LIGUE_1",    "Marseille",            "Paris Saint-Germain"),
]


def _get_upcoming_from_db(db: Session, limit: int) -> list[dict]:
    """Pull genuinely scheduled fixtures from the DB, ordered soonest first."""
    today = datetime.date.today()
    today_dt = datetime.datetime.combine(today, datetime.time.min)
    cutoff_dt = datetime.datetime.combine(today + datetime.timedelta(days=30), datetime.time.max)

    rows = (
        db.query(Fixture, Season, League)
        .join(Season, Season.id == Fixture.season_id)
        .join(League, League.id == Season.league_id)
        .filter(
            Fixture.status == "SCHEDULED",
            Fixture.fixture_date >= today_dt,
            Fixture.fixture_date <= cutoff_dt,
            # Skip fixtures that already have a result
            ~Fixture.id.in_(
                db.query(MatchResult.fixture_id)
            ),
        )
        .order_by(Fixture.fixture_date.asc())
        .limit(limit)
        .all()
    )

    result = []
    for fixture, season, league in rows:
        home = db.query(Team).filter_by(id=fixture.home_team_id).first()
        away = db.query(Team).filter_by(id=fixture.away_team_id).first()
        if not home or not away:
            continue
        result.append({
            "leagueCode": league.code,
            "leagueName": league.name,
            "season": season.label,
            "homeTeamId": fixture.home_team_id,
            "homeTeamName": home.name,
            "awayTeamId": fixture.away_team_id,
            "awayTeamName": away.name,
            "fixtureDate": fixture.fixture_date.date().isoformat(),
        })
    return result


def _get_showcase(db: Session, limit: int) -> list[dict]:
    """Build showcase matchups for leagues not yet started (pre-season)."""
    today = datetime.date.today()
    month = today.month
    year = today.year
    # Next domestic season starts in August
    next_season_start = datetime.date(year if month < 8 else year, 8, 9)
    results = []
    for i, (league_code, home_name, away_name) in enumerate(SHOWCASE[:limit]):
        league = db.query(League).filter_by(code=league_code).first()
        if not league:
            continue
        home = db.query(Team).filter_by(name=home_name).first()
        away = db.query(Team).filter_by(name=away_name).first()
        if not home or not away:
            continue
        season_label = f"{year}/{year + 1}" if month >= 8 else f"{year}/{year + 1}"
        # Spread showcase across the opening weekend
        fixture_date = (next_season_start + datetime.timedelta(days=i % 3)).isoformat()
        results.append({
            "leagueCode": league_code,
            "leagueName": league.name,
            "season": season_label,
            "homeTeamId": home.id,
            "homeTeamName": home.name,
            "awayTeamId": away.id,
            "awayTeamName": away.name,
            "fixtureDate": fixture_date,
            "isShowcase": True,
        })
    return results


def _run_prediction(db: Session, matchup: dict) -> Optional[dict]:
    """Run a single prediction for a matchup dict and return a compact result."""
    from temfpa.api.routes.predict import _elo_fallback, _load_ensemble, _load_poisson
    from temfpa.config import settings
    from temfpa.features.pipeline import build_feature_vector
    from temfpa.models.scoreline import most_likely_score, top_k_scorelines

    import pandas as pd

    home_team_id = matchup["homeTeamId"]
    away_team_id = matchup["awayTeamId"]
    fixture_date = datetime.date.fromisoformat(matchup["fixtureDate"])

    # Season lookup
    league = db.query(League).filter_by(code=matchup["leagueCode"]).first()
    season = (
        db.query(Season)
        .filter_by(league_id=league.id if league else 0, label=matchup["season"])
        .first()
    ) if league else None
    season_id = season.id if season else 0

    # Feature vector
    try:
        fv = build_feature_vector(db, home_team_id, away_team_id, season_id, fixture_date)
    except Exception:
        fv = {}
    X = pd.DataFrame([fv]) if fv else pd.DataFrame([{}])

    # Use Elo when no league-specific history
    league_finished = (
        db.query(Fixture)
        .join(MatchResult, MatchResult.fixture_id == Fixture.id)
        .filter(Fixture.season_id == season_id, Fixture.status == "FINISHED")
        .count()
    ) if season_id else 0

    has_real_data = (
        league_finished >= 10
        and fv.get("h2h_total", 0) > 0
    )

    neutral_venue = matchup["leagueCode"] == "WORLD_CUP"

    save_dir = settings.MODEL_DIR
    ensemble = _load_ensemble(save_dir)
    poisson = _load_poisson(save_dir)

    if ensemble and not X.empty and len(X.columns) > 0 and has_real_data:
        try:
            result_key, confidence, probs = ensemble.predict_outcome(X)
        except Exception:
            result_key, confidence, probs = _elo_fallback(db, home_team_id, away_team_id, neutral_venue=neutral_venue)
    else:
        result_key, confidence, probs = _elo_fallback(db, home_team_id, away_team_id, neutral_venue=neutral_venue)

    if poisson and not X.empty and len(X.columns) > 0 and has_real_data:
        try:
            lh, la = poisson.predict(X)
        except Exception:
            hs = probs.get("home", 0.45) / 0.45
            aws = probs.get("away", 0.30) / 0.30
            lh = max(0.5, min(4.0, 1.5 * hs))
            la = max(0.5, min(4.0, 1.2 * aws))
    else:
        hs = probs.get("home", 0.45) / 0.45
        aws = probs.get("away", 0.30) / 0.30
        lh = max(0.5, min(4.0, 1.5 * hs))
        la = max(0.5, min(4.0, 1.2 * aws))

    RESULT_DISPLAY = {"home": "Home Win", "draw": "Draw", "away": "Away Win"}
    top3 = top_k_scorelines(lh, la, k=3)

    return {
        "league": matchup["leagueName"],
        "leagueCode": matchup["leagueCode"],
        "season": matchup["season"],
        "fixtureDate": matchup["fixtureDate"],
        "homeTeam": {"id": home_team_id, "name": matchup["homeTeamName"]},
        "awayTeam": {"id": away_team_id, "name": matchup["awayTeamName"]},
        "result": RESULT_DISPLAY.get(result_key, result_key),
        "resultKey": result_key,
        "confidence": confidence,
        "homeWinProbability": round(probs.get("home", 0.45), 3),
        "drawProbability": round(probs.get("draw", 0.25), 3),
        "awayWinProbability": round(probs.get("away", 0.30), 3),
        "likelyScore": most_likely_score(lh, la),
        "topScorelines": [
            {"score": s["score"], "probability": round(s["probability"], 3)}
            for s in top3
        ],
    }


@router.get("/api/v2/upcoming-predictions")
def upcoming_predictions(limit: int = 8, db: Session = Depends(get_db)):
    """Return proactive predictions for upcoming or featured matches."""
    cache_key = f"upcoming_{limit}"
    cached = _UPCOMING_CACHE.get(cache_key)
    if cached and (_time.time() - cached["ts"]) < _CACHE_TTL:
        return cached["data"]

    matchups = _get_upcoming_from_db(db, limit)

    # Fill with showcase if not enough real scheduled fixtures
    if len(matchups) < limit:
        showcase = _get_showcase(db, limit - len(matchups))
        matchups.extend(showcase)

    predictions = []
    for matchup in matchups:
        try:
            pred = _run_prediction(db, matchup)
            if pred:
                predictions.append(pred)
                try:
                    log_prediction(db, matchup=matchup, prediction=pred, source="upcoming")
                except Exception as log_exc:
                    logger.warning("Failed to log prediction: %s", log_exc)
        except Exception as exc:
            logger.warning("Skipping matchup %s: %s", matchup, exc)

    _UPCOMING_CACHE[cache_key] = {"ts": _time.time(), "data": predictions}
    return predictions
