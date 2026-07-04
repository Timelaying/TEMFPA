"""League and team listing endpoints."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from temfpa.api.dependencies import get_db
from temfpa.db.models import League, LeagueSeasonTeam, Season, Team

router = APIRouter()


@router.get("/api/v2/leagues")
def get_leagues(db: Session = Depends(get_db)):
    """Return all leagues from DB."""
    leagues = db.query(League).order_by(League.name).all()
    return [
        {
            "id": lg.id,
            "code": lg.code,
            "name": lg.name,
            "country": lg.country,
            "tier": lg.tier,
        }
        for lg in leagues
    ]


@router.get("/api/v2/teams/{league_code}")
def get_teams(
    league_code: str,
    season: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Return teams for a league, optionally filtered by season."""
    league = db.query(League).filter(League.code == league_code).first()
    if not league:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"League '{league_code}' not found")

    query = (
        db.query(Team)
        .join(LeagueSeasonTeam, LeagueSeasonTeam.team_id == Team.id)
        .filter(LeagueSeasonTeam.league_id == league.id)
    )

    if season:
        query = (
            query.join(Season, Season.id == LeagueSeasonTeam.season_id)
            .filter(Season.label == season)
        )

    teams = query.distinct().order_by(Team.name).all()

    return [
        {
            "id": t.id,
            "name": t.name,
            "shortName": t.short_name,
            "country": t.country,
        }
        for t in teams
    ]
