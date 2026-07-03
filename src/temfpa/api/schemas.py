"""Pydantic schemas for the TEMFPA V.2 API."""

from __future__ import annotations

import datetime
from typing import Any, Optional

from pydantic import BaseModel


class PredictionRequest(BaseModel):
    leagueId: str
    season: str
    homeTeamId: int
    awayTeamId: int
    fixtureDate: datetime.date
    includePlayerImpact: bool = True
    includeFormationImpact: bool = True
    includeScorePrediction: bool = True


class ScorelineOption(BaseModel):
    score: str
    homeGoals: int
    awayGoals: int
    probability: float


class KeyFactor(BaseModel):
    factor: str
    description: str
    impact: str  # "positive" | "negative" | "neutral"
    direction: str  # "home" | "away" | "neutral"


class TeamFormInfo(BaseModel):
    formLast5: str  # "W-D-L-W-L"
    goalsPerGame: float
    concededPerGame: float
    position: Optional[int] = None


class TeamComparison(BaseModel):
    homeForm: TeamFormInfo
    awayForm: TeamFormInfo


class FormationImpact(BaseModel):
    homeFormation: Optional[str]
    awayFormation: Optional[str]
    homeFormationWinPercent: Optional[float]
    awayFormationWinPercent: Optional[float]
    formationComment: str


class PlayerImpactEntry(BaseModel):
    playerName: str
    team: str
    status: str
    teamWinPercentWithPlayer: float
    teamWinPercentWithoutPlayer: float
    impactComment: str


class FixtureInfo(BaseModel):
    league: str
    season: str
    homeTeam: dict[str, Any]  # {"id": int, "name": str}
    awayTeam: dict[str, Any]
    date: str


class PredictionCore(BaseModel):
    result: str  # "Home Win" | "Draw" | "Away Win"
    confidence: str
    homeWinProbability: float
    drawProbability: float
    awayWinProbability: float
    predictedHomeGoals: float
    predictedAwayGoals: float
    likelyScore: str


class PredictionResponse(BaseModel):
    fixture: FixtureInfo
    prediction: PredictionCore
    topScorelines: list[ScorelineOption]
    keyFactors: list[KeyFactor]
    teamComparison: TeamComparison
    formationImpact: Optional[FormationImpact] = None
    playerImpact: Optional[list[PlayerImpactEntry]] = None


class ErrorResponse(BaseModel):
    error: str
    code: str
    details: Optional[str] = None
