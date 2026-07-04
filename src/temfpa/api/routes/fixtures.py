"""Fixture listing endpoints."""

from __future__ import annotations

import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from temfpa.api.dependencies import get_db
from temfpa.db.models import Fixture, League, Season, Team

router = APIRouter()


@router.get("/api/v2/fixtures")
def get_fixtures(
    leagueId: Optional[str] = Query(None),
    season: Optional[str] = Query(None),
    from_date: Optional[datetime.date] = Query(None),
    to_date: Optional[datetime.date] = Query(None),
    db: Session = Depends(get_db),
):
    """Return fixtures with optional filters."""
    query = db.query(Fixture)

    if leagueId:
        league = db.query(League).filter(League.code == leagueId).first()
        if not league:
            return []
        season_query = db.query(Season.id).filter(Season.league_id == league.id)
        if season:
            season_query = season_query.filter(Season.label == season)
        season_ids = [row[0] for row in season_query.all()]
        if not season_ids:
            return []
        query = query.filter(Fixture.season_id.in_(season_ids))
    elif season:
        season_rows = db.query(Season.id).filter(Season.label == season).all()
        season_ids = [row[0] for row in season_rows]
        if season_ids:
            query = query.filter(Fixture.season_id.in_(season_ids))

    if from_date:
        from_dt = datetime.datetime.combine(from_date, datetime.time.min)
        query = query.filter(Fixture.fixture_date >= from_dt)
    if to_date:
        to_dt = datetime.datetime.combine(to_date, datetime.time.max)
        query = query.filter(Fixture.fixture_date <= to_dt)

    fixtures = query.order_by(Fixture.fixture_date.asc()).limit(100).all()

    result = []
    for f in fixtures:
        home_team = db.query(Team).filter(Team.id == f.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == f.away_team_id).first()
        result.append({
            "id": f.id,
            "date": f.fixture_date.isoformat() if f.fixture_date else None,
            "status": f.status,
            "matchweek": f.matchweek,
            "homeTeam": {"id": home_team.id, "name": home_team.name} if home_team else None,
            "awayTeam": {"id": away_team.id, "name": away_team.name} if away_team else None,
        })

    return result
