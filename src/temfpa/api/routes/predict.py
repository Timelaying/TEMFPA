"""Main prediction endpoint."""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from temfpa.api.dependencies import get_db
from temfpa.api.schemas import (
    FixtureInfo,
    FormationImpact,
    KeyFactor,
    PlayerImpactEntry,
    PredictionCore,
    PredictionRequest,
    PredictionResponse,
    ScorelineOption,
    TeamComparison,
    TeamFormInfo,
)
from temfpa.config import settings
from temfpa.db.models import (
    Fixture,
    InjuryOrAbsence,
    League,
    Lineup,
    MatchResult,
    Player,
    Prediction,
    PredictionExplanation,
    PredictionScoreline,
    Season,
    Team,
)
from temfpa.explainability.factors import build_narrative, derive_key_factors
from temfpa.features.formation import get_formation_win_rate
from temfpa.features.pipeline import build_feature_vector
from temfpa.features.player_availability import get_player_impact
from temfpa.features.team_form import get_team_form
from temfpa.models.ensemble import EnsemblePredictor
from temfpa.models.poisson import PoissonGoalModel
from temfpa.models.scoreline import most_likely_score, top_k_scorelines

router = APIRouter()

RESULT_DISPLAY = {"home": "Home Win", "draw": "Draw", "away": "Away Win"}


def _load_ensemble(save_dir: Path) -> Optional[EnsemblePredictor]:
    ensemble_path = save_dir / "ensemble.joblib"
    if ensemble_path.exists():
        try:
            return EnsemblePredictor.load(ensemble_path)
        except Exception:
            return None
    return None


def _load_poisson(save_dir: Path) -> Optional[PoissonGoalModel]:
    poisson_path = save_dir / "poisson.joblib"
    if poisson_path.exists():
        try:
            model = PoissonGoalModel()
            model.load(poisson_path)
            return model
        except Exception:
            return None
    return None


def _build_form_string(db: Session, team_id: int, before_date: datetime.date, n: int = 5) -> str:
    """Build form string like 'W-D-L-W-L' from recent results."""
    before_dt = datetime.datetime.combine(before_date, datetime.time.max)
    from sqlalchemy import or_
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
    letters = []
    for fixture, result in reversed(rows):
        is_home = fixture.home_team_id == team_id
        if result.winner == "draw":
            letters.append("D")
        elif (is_home and result.winner == "home") or (not is_home and result.winner == "away"):
            letters.append("W")
        else:
            letters.append("L")
    return "-".join(letters) if letters else "N/A"


def _get_recent_formation(db: Session, team_id: int, before_date: datetime.date) -> Optional[str]:
    """Get the most recently used formation for a team."""
    before_dt = datetime.datetime.combine(before_date, datetime.time.max)
    lineup = (
        db.query(Lineup)
        .join(Fixture, Fixture.id == Lineup.fixture_id)
        .filter(
            Lineup.team_id == team_id,
            Fixture.fixture_date < before_dt,
            Lineup.formation.isnot(None),
        )
        .order_by(Fixture.fixture_date.desc())
        .first()
    )
    return lineup.formation if lineup else None


def _compute_request_hash(req: PredictionRequest) -> str:
    payload = json.dumps(
        {
            "leagueId": req.leagueId,
            "season": req.season,
            "homeTeamId": req.homeTeamId,
            "awayTeamId": req.awayTeamId,
            "fixtureDate": req.fixtureDate.isoformat(),
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


@router.post("/api/v2/predict", response_model=PredictionResponse)
def predict(req: PredictionRequest, db: Session = Depends(get_db)):
    """Main prediction endpoint."""

    # --- Validate teams ---
    home_team = db.query(Team).filter(Team.id == req.homeTeamId).first()
    if not home_team:
        raise HTTPException(status_code=404, detail=f"Home team {req.homeTeamId} not found")

    away_team = db.query(Team).filter(Team.id == req.awayTeamId).first()
    if not away_team:
        raise HTTPException(status_code=404, detail=f"Away team {req.awayTeamId} not found")

    # --- Validate league ---
    league = db.query(League).filter(League.code == req.leagueId).first()
    if not league:
        raise HTTPException(status_code=404, detail=f"League '{req.leagueId}' not found")

    # --- Look up season ---
    season = (
        db.query(Season)
        .filter(Season.league_id == league.id, Season.label == req.season)
        .first()
    )
    season_id = season.id if season else 0

    # --- Build feature vector ---
    fixture_date = req.fixtureDate
    try:
        fv = build_feature_vector(
            db,
            home_team_id=req.homeTeamId,
            away_team_id=req.awayTeamId,
            season_id=season_id,
            fixture_date=fixture_date,
        )
    except Exception as exc:
        fv = {}

    X = pd.DataFrame([fv]) if fv else pd.DataFrame([{}])

    # --- Load or build ensemble ---
    save_dir = settings.MODEL_DIR
    ensemble = _load_ensemble(save_dir)
    poisson = _load_poisson(save_dir)

    # Detect whether we have real match history for these teams *in this league*.
    # For cross-league competitions (UCL), EPL form for Man City should not drive
    # the prediction — only use the ensemble when there is league-specific history.
    league_finished = (
        db.query(Fixture)
        .join(MatchResult, MatchResult.fixture_id == Fixture.id)
        .filter(
            Fixture.season_id == season_id,
            Fixture.status == "FINISHED",
        )
        .count()
    ) if season_id else 0

    has_real_data = (
        league_finished >= 10
        and fv.get("h2h_total", 0) > 0
    )

    # --- Predict outcome ---
    # Only use saved ensemble if it exists AND we have real feature data.
    # Never auto-train during a prediction request — that risks persisting
    # models trained on empty/tiny datasets.
    neutral_venue = (league.code == "WORLD_CUP")

    if ensemble is not None and not X.empty and len(X.columns) > 0 and has_real_data:
        try:
            result_key, confidence, probs = ensemble.predict_outcome(X)
        except Exception:
            result_key, confidence, probs = _elo_fallback(db, req.homeTeamId, req.awayTeamId, neutral_venue)
    else:
        result_key, confidence, probs = _elo_fallback(db, req.homeTeamId, req.awayTeamId, neutral_venue)

    # --- Predict goals ---
    if poisson is not None and not X.empty and len(X.columns) > 0:
        try:
            lambda_home, lambda_away = poisson.predict(X)
        except Exception:
            # Derive expected goals from Elo win probabilities.
            # League average: 1.5 home goals, 1.2 away goals per match.
            # Scale by team relative strength from the Elo probs.
            # A team with 70% win prob should score more than league avg.
            home_strength = probs.get("home", 0.45) / 0.45  # ratio to league avg home win rate
            away_strength = probs.get("away", 0.30) / 0.30
            lambda_home = max(0.5, min(4.0, 1.5 * home_strength))
            lambda_away = max(0.5, min(4.0, 1.2 * away_strength))
    else:
        # Derive expected goals from Elo win probabilities.
        # League average: 1.5 home goals, 1.2 away goals per match.
        # Scale by team relative strength from the Elo probs.
        # A team with 70% win prob should score more than league avg.
        home_strength = probs.get("home", 0.45) / 0.45  # ratio to league avg home win rate
        away_strength = probs.get("away", 0.30) / 0.30
        lambda_home = max(0.5, min(4.0, 1.5 * home_strength))
        lambda_away = max(0.5, min(4.0, 1.2 * away_strength))

    # --- Scorelines ---
    if req.includeScorePrediction:
        scorelines = top_k_scorelines(lambda_home, lambda_away, k=3)
        top_scorelines = [
            ScorelineOption(
                score=s["score"],
                homeGoals=s["homeGoals"],
                awayGoals=s["awayGoals"],
                probability=round(s["probability"], 4),
            )
            for s in scorelines
        ]
        likely_score = most_likely_score(lambda_home, lambda_away)
    else:
        top_scorelines = []
        likely_score = "1-1"

    # --- Team comparison ---
    home_form_stats = get_team_form(db, req.homeTeamId, fixture_date, n_matches=5)
    away_form_stats = get_team_form(db, req.awayTeamId, fixture_date, n_matches=5)
    home_form_str = _build_form_string(db, req.homeTeamId, fixture_date, n=5)
    away_form_str = _build_form_string(db, req.awayTeamId, fixture_date, n=5)

    team_comparison = TeamComparison(
        homeForm=TeamFormInfo(
            formLast5=home_form_str,
            goalsPerGame=round(home_form_stats.get("goals_scored_avg", 1.0), 2),
            concededPerGame=round(home_form_stats.get("goals_conceded_avg", 1.0), 2),
        ),
        awayForm=TeamFormInfo(
            formLast5=away_form_str,
            goalsPerGame=round(away_form_stats.get("goals_scored_avg", 1.0), 2),
            concededPerGame=round(away_form_stats.get("goals_conceded_avg", 1.0), 2),
        ),
    )

    # --- Formation impact ---
    formation_impact_obj: Optional[FormationImpact] = None
    if req.includeFormationImpact:
        home_formation = _get_recent_formation(db, req.homeTeamId, fixture_date)
        away_formation = _get_recent_formation(db, req.awayTeamId, fixture_date)

        home_form_wr = None
        away_form_wr = None
        comment_parts = []

        if home_formation:
            stats = get_formation_win_rate(db, req.homeTeamId, home_formation, fixture_date, n=20)
            home_form_wr = round(stats["win_rate"] * 100, 1) if stats["matches"] > 0 else None
            if home_form_wr is not None:
                comment_parts.append(
                    f"{home_team.name} wins {home_form_wr}% with {home_formation}"
                )

        if away_formation:
            stats = get_formation_win_rate(db, req.awayTeamId, away_formation, fixture_date, n=20)
            away_form_wr = round(stats["win_rate"] * 100, 1) if stats["matches"] > 0 else None
            if away_form_wr is not None:
                comment_parts.append(
                    f"{away_team.name} wins {away_form_wr}% with {away_formation}"
                )

        comment = ". ".join(comment_parts) if comment_parts else "No formation data available."

        formation_impact_obj = FormationImpact(
            homeFormation=home_formation,
            awayFormation=away_formation,
            homeFormationWinPercent=home_form_wr,
            awayFormationWinPercent=away_form_wr,
            formationComment=comment,
        )

    # --- Player impact ---
    player_impact_list: Optional[list[PlayerImpactEntry]] = None
    if req.includePlayerImpact:
        absences = (
            db.query(InjuryOrAbsence, Player)
            .join(Player, Player.id == InjuryOrAbsence.player_id)
            .filter(
                InjuryOrAbsence.team_id.in_([req.homeTeamId, req.awayTeamId]),
                (InjuryOrAbsence.end_date.is_(None))
                | (InjuryOrAbsence.end_date >= fixture_date),
                (InjuryOrAbsence.start_date.is_(None))
                | (InjuryOrAbsence.start_date <= fixture_date),
            )
            .all()
        )

        player_impact_list = []
        for absence, player in absences:
            team_name = home_team.name if absence.team_id == req.homeTeamId else away_team.name
            impact = get_player_impact(
                db, player.id, absence.team_id, fixture_date, n=20
            )
            comment = (
                f"Impact score: {impact['impact_score']:+.2f} "
                f"(win% with: {impact['win_pct_with']:.0%}, without: {impact['win_pct_without']:.0%})"
            )
            player_impact_list.append(
                PlayerImpactEntry(
                    playerName=player.name,
                    team=team_name,
                    status=absence.reason or "unavailable",
                    teamWinPercentWithPlayer=round(impact["win_pct_with"] * 100, 1),
                    teamWinPercentWithoutPlayer=round(impact["win_pct_without"] * 100, 1),
                    impactComment=comment,
                )
            )

    # --- Key factors ---
    raw_factors = derive_key_factors(fv, probs, home_team.name, away_team.name)
    key_factors = [KeyFactor(**f) for f in raw_factors]

    # --- Narrative for explanation ---
    narrative = build_narrative(raw_factors, home_team.name, away_team.name, result_key, confidence)

    # --- Persist to DB ---
    request_hash = _compute_request_hash(req)
    # Look up or create fixture record
    fixture_record = (
        db.query(Fixture)
        .filter(
            Fixture.home_team_id == req.homeTeamId,
            Fixture.away_team_id == req.awayTeamId,
            Fixture.season_id == season_id,
        )
        .order_by(Fixture.fixture_date.desc())
        .first()
    )

    existing = (
        db.query(Prediction)
        .filter(
            Prediction.request_hash == request_hash,
            Prediction.model_version == settings.MODEL_VERSION,
        )
        .first()
    )
    if existing:
        pred_record = existing
    else:
        pred_record = Prediction(
            fixture_id=fixture_record.id if fixture_record else None,
            request_hash=request_hash,
            model_version=settings.MODEL_VERSION,
            result=result_key,
            confidence=confidence,
            home_win_prob=probs.get("home"),
            draw_prob=probs.get("draw"),
            away_win_prob=probs.get("away"),
            predicted_home_goals=lambda_home,
            predicted_away_goals=lambda_away,
            likely_score=likely_score,
        )
        db.add(pred_record)
        db.flush()

        # Scorelines
        for rank, sl in enumerate(top_scorelines, start=1):
            db.add(
                PredictionScoreline(
                    prediction_id=pred_record.id,
                    home_goals=sl.homeGoals,
                    away_goals=sl.awayGoals,
                    probability=sl.probability,
                    rank=rank,
                )
            )

        # Explanation
        db.add(
            PredictionExplanation(
                prediction_id=pred_record.id,
                key_factors=raw_factors,
                narrative=narrative,
            )
        )
        db.commit()

    # --- Log to PredictionLog for accuracy tracking ---
    try:
        from temfpa.db.prediction_log_service import log_prediction
        _matchup = {
            "leagueCode": league.code,
            "homeTeamId": req.homeTeamId,
            "awayTeamId": req.awayTeamId,
            "fixtureDate": req.fixtureDate.isoformat(),
        }
        _pred = {
            "resultKey": result_key,
            "confidence": confidence,
            "homeWinProbability": round(probs.get("home", 0.45), 4),
            "drawProbability": round(probs.get("draw", 0.25), 4),
            "awayWinProbability": round(probs.get("away", 0.30), 4),
            "likelyScore": likely_score,
        }
        log_prediction(db, matchup=_matchup, prediction=_pred, source="manual")
    except Exception:
        pass  # never let logging break a prediction response

    # --- Build response ---
    return PredictionResponse(
        fixture=FixtureInfo(
            league=league.name,
            season=req.season,
            homeTeam={"id": home_team.id, "name": home_team.name},
            awayTeam={"id": away_team.id, "name": away_team.name},
            date=fixture_date.isoformat(),
        ),
        prediction=PredictionCore(
            result=RESULT_DISPLAY.get(result_key, result_key),
            confidence=confidence,
            homeWinProbability=round(probs.get("home", 0.45), 4),
            drawProbability=round(probs.get("draw", 0.25), 4),
            awayWinProbability=round(probs.get("away", 0.30), 4),
            predictedHomeGoals=round(lambda_home, 2),
            predictedAwayGoals=round(lambda_away, 2),
            likelyScore=likely_score,
        ),
        topScorelines=top_scorelines,
        keyFactors=key_factors,
        teamComparison=team_comparison,
        formationImpact=formation_impact_obj,
        playerImpact=player_impact_list if req.includePlayerImpact else None,
    )


def _elo_fallback(db, home_team_id: int, away_team_id: int, neutral_venue: bool = False) -> tuple[str, str, dict]:
    """Fallback: use Elo-based probabilities."""
    try:
        from temfpa.models.elo import EloRating
        elo = EloRating.build_from_db(db)
        if neutral_venue:
            elo.HOME_ADVANTAGE = 0.0
        h, d, a = elo.expected_home_win_prob(home_team_id, away_team_id)
        probs = {"home": h, "draw": d, "away": a}
        max_prob = max(h, d, a)
        if h >= d and h >= a:
            result = "home"
        elif a >= h and a >= d:
            result = "away"
        else:
            result = "draw"
        confidence = "High" if max_prob > 0.55 else "Medium" if max_prob > 0.42 else "Low"
        return result, confidence, probs
    except Exception:
        return "draw", "Low", {"home": 0.35, "draw": 0.30, "away": 0.35}
