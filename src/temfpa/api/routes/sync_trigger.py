"""Sync trigger endpoint — kicks off a background data sync.

POST /api/v2/sync
Body: {"league": "WORLD_CUP", "season": "2026", "skip_lineups": true, "skip_player_stats": true}
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()


class SyncRequest(BaseModel):
    league: str
    season: str
    skip_lineups: bool = True
    skip_player_stats: bool = True


def _do_sync(league: str, season: str, skip_lineups: bool, skip_player_stats: bool) -> None:
    try:
        from temfpa.ingestion.sync import run_full_sync
        run_full_sync(
            league_code=league,
            season_label=season,
            skip_lineups=skip_lineups,
            skip_player_stats=skip_player_stats,
        )
        logger.info("Background sync complete: %s %s", league, season)
    except Exception:
        logger.exception("Background sync failed: %s %s", league, season)


@router.post("/api/v2/sync")
def trigger_sync(req: SyncRequest, background_tasks: BackgroundTasks):
    """Trigger a background data sync. Returns immediately."""
    background_tasks.add_task(
        _do_sync,
        league=req.league,
        season=req.season,
        skip_lineups=req.skip_lineups,
        skip_player_stats=req.skip_player_stats,
    )
    return {
        "status": "queued",
        "league": req.league,
        "season": req.season,
        "message": f"Sync started for {req.league} {req.season}. Check server logs for progress.",
    }


@router.get("/api/v2/sync/leagues")
def sync_leagues():
    """Return the list of syncable leagues and their default seasons."""
    return [
        {"league": "WORLD_CUP", "season": "2026", "label": "FIFA World Cup 2026"},
        {"league": "EPL", "season": "2024/2025", "label": "Premier League 2024/25"},
        {"league": "LA_LIGA", "season": "2024/2025", "label": "La Liga 2024/25"},
        {"league": "BUNDESLIGA", "season": "2024/2025", "label": "Bundesliga 2024/25"},
        {"league": "SERIE_A", "season": "2024/2025", "label": "Serie A 2024/25"},
        {"league": "LIGUE_1", "season": "2024/2025", "label": "Ligue 1 2024/25"},
    ]
