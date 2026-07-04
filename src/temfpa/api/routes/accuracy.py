"""Prediction accuracy endpoint.

GET /api/v2/predictions/accuracy
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from temfpa.api.dependencies import get_db
from temfpa.db.models import PredictionLog, Team

router = APIRouter()

RECENT_LIMIT = 20


def _team_name(db: Session, team_id: int) -> str:
    t = db.query(Team).filter_by(id=team_id).first()
    return t.name if t else str(team_id)


@router.get("/api/v2/predictions/accuracy")
def prediction_accuracy(league: str | None = None, db: Session = Depends(get_db)):
    """Return overall, by-confidence, by-league, rolling trend, and recent prediction accuracy.

    Optional ?league=EPL filter for the recent list.
    """

    # --- All resolved rows ---
    resolved_q = db.query(PredictionLog).filter(PredictionLog.is_correct.isnot(None))
    resolved = resolved_q.all()

    total = len(resolved)
    correct = sum(1 for r in resolved if r.is_correct)

    # Brier score: mean of squared probability errors across all outcomes
    # Lower is better (0 = perfect, 2 = worst possible)
    brier_scores = []
    for r in resolved:
        ph = r.home_win_prob or 0.33
        pd_ = r.draw_prob or 0.33
        pa = r.away_win_prob or 0.34
        ah = 1.0 if r.actual_result == "home" else 0.0
        ad = 1.0 if r.actual_result == "draw" else 0.0
        aa = 1.0 if r.actual_result == "away" else 0.0
        brier_scores.append((ph - ah) ** 2 + (pd_ - ad) ** 2 + (pa - aa) ** 2)

    brier_avg = round(sum(brier_scores) / len(brier_scores), 4) if brier_scores else None

    overall = {
        "total": total,
        "correct": correct,
        "accuracy_pct": round(correct / total * 100, 1) if total else 0.0,
        "brier_score": brier_avg,
    }

    # --- By confidence ---
    by_confidence: dict[str, dict] = {}
    for row in resolved:
        b = row.predicted_confidence
        if b not in by_confidence:
            by_confidence[b] = {"total": 0, "correct": 0, "accuracy_pct": 0.0}
        by_confidence[b]["total"] += 1
        if row.is_correct:
            by_confidence[b]["correct"] += 1
    for b, d in by_confidence.items():
        d["accuracy_pct"] = round(d["correct"] / d["total"] * 100, 1) if d["total"] else 0.0

    # --- By league ---
    by_league: dict[str, dict] = {}
    for row in resolved:
        c = row.league_code
        if c not in by_league:
            by_league[c] = {"total": 0, "correct": 0, "accuracy_pct": 0.0}
        by_league[c]["total"] += 1
        if row.is_correct:
            by_league[c]["correct"] += 1
    for c, d in by_league.items():
        d["accuracy_pct"] = round(d["correct"] / d["total"] * 100, 1) if d["total"] else 0.0

    # --- Rolling accuracy trend (last 30 resolved, chronological) ---
    trend_rows = (
        db.query(PredictionLog)
        .filter(PredictionLog.is_correct.isnot(None))
        .order_by(PredictionLog.fixture_date.asc())
        .limit(30)
        .all()
    )
    running_correct = 0
    trend = []
    for i, r in enumerate(trend_rows, 1):
        if r.is_correct:
            running_correct += 1
        trend.append({
            "n": i,
            "fixture_date": r.fixture_date.isoformat(),
            "is_correct": r.is_correct,
            "cumulative_accuracy": round(running_correct / i * 100, 1),
        })

    # --- Recent (all, including unresolved; filterable by league) ---
    recent_q = db.query(PredictionLog)
    if league:
        recent_q = recent_q.filter(PredictionLog.league_code == league)
    recent_rows = recent_q.order_by(PredictionLog.created_at.desc()).limit(RECENT_LIMIT).all()

    recent = [
        {
            "id": r.id,
            "league_code": r.league_code,
            "home_team": _team_name(db, r.home_team_id),
            "away_team": _team_name(db, r.away_team_id),
            "fixture_date": r.fixture_date.isoformat(),
            "predicted_result": r.predicted_result,
            "predicted_confidence": r.predicted_confidence,
            "home_win_prob": r.home_win_prob,
            "draw_prob": r.draw_prob,
            "away_win_prob": r.away_win_prob,
            "likely_score": r.likely_score,
            "actual_result": r.actual_result,
            "actual_home_goals": r.actual_home_goals,
            "actual_away_goals": r.actual_away_goals,
            "is_correct": r.is_correct,
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        }
        for r in recent_rows
    ]

    return {
        "overall": overall,
        "by_confidence": by_confidence,
        "by_league": by_league,
        "trend": trend,
        "recent": recent,
    }
