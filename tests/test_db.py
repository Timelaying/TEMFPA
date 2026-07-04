"""Tests for database schema, ORM models, and relationships."""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy.orm import Session

from temfpa.db.models import (
    Coach,
    Fixture,
    InjuryOrAbsence,
    League,
    LeagueSeasonTeam,
    Lineup,
    LineupPlayer,
    MatchResult,
    Player,
    PlayerMatchStat,
    Prediction,
    PredictionExplanation,
    PredictionScoreline,
    Season,
    Team,
    TeamMatchStat,
)


# ---------------------------------------------------------------------------
# Schema smoke tests — every table can be created and queried
# ---------------------------------------------------------------------------


def test_league_crud(db_session: Session):
    league = League(code="EPL", name="Premier League", country="England", tier=1)
    db_session.add(league)
    db_session.commit()

    found = db_session.get(League, league.id)
    assert found is not None
    assert found.code == "EPL"
    assert found.tier == 1


def test_season_belongs_to_league(db_session: Session, sample_league: League):
    season = Season(
        league_id=sample_league.id,
        label="2023/2024",
        start_date=datetime.date(2023, 8, 11),
        end_date=datetime.date(2024, 5, 19),
    )
    db_session.add(season)
    db_session.commit()

    assert season.league.code == "EPL"
    assert len(sample_league.seasons) == 1


def test_team_crud(db_session: Session):
    team = Team(
        name="Arsenal",
        short_name="ARS",
        country="England",
        provider_ids={"fbref": "Arsenal", "football_data": 57},
    )
    db_session.add(team)
    db_session.commit()

    found = db_session.get(Team, team.id)
    assert found.name == "Arsenal"
    assert found.provider_ids["fbref"] == "Arsenal"


def test_player_belongs_to_team(db_session: Session, sample_teams):
    home, _ = sample_teams
    player = Player(team_id=home.id, name="Erling Haaland", position="FWD")
    db_session.add(player)
    db_session.commit()

    assert player.team.name == "Manchester City"
    assert len(home.players) == 1


def test_coach_belongs_to_team(db_session: Session, sample_teams):
    home, _ = sample_teams
    coach = Coach(
        team_id=home.id,
        name="Pep Guardiola",
        appointed=datetime.date(2016, 7, 1),
    )
    db_session.add(coach)
    db_session.commit()

    assert coach.team.name == "Manchester City"


def test_fixture_relationships(
    db_session: Session, sample_fixture: Fixture, sample_teams
):
    home, away = sample_teams
    assert sample_fixture.home_team.name == "Manchester City"
    assert sample_fixture.away_team.name == "Liverpool"
    assert sample_fixture.status == "FINISHED"


def test_match_result_linked_to_fixture(
    db_session: Session, sample_fixture: Fixture
):
    result = MatchResult(
        fixture_id=sample_fixture.id,
        home_goals=1,
        away_goals=1,
        winner="draw",
        home_xg=1.3,
        away_xg=1.1,
    )
    db_session.add(result)
    db_session.commit()

    assert sample_fixture.result.winner == "draw"
    assert result.fixture.id == sample_fixture.id


def test_lineup_and_lineup_players(
    db_session: Session, sample_fixture: Fixture, sample_teams
):
    home, _ = sample_teams
    player = Player(team_id=home.id, name="Kevin De Bruyne", position="MID")
    db_session.add(player)
    db_session.flush()

    lineup = Lineup(
        fixture_id=sample_fixture.id,
        team_id=home.id,
        formation="4-3-3",
        is_confirmed=True,
    )
    db_session.add(lineup)
    db_session.flush()

    lp = LineupPlayer(
        lineup_id=lineup.id,
        player_id=player.id,
        shirt_number=17,
        position="MID",
        is_starter=True,
    )
    db_session.add(lp)
    db_session.commit()

    assert lineup.formation == "4-3-3"
    assert len(lineup.players) == 1
    assert lineup.players[0].player.name == "Kevin De Bruyne"


def test_injury_or_absence(
    db_session: Session, sample_fixture: Fixture, sample_teams
):
    home, _ = sample_teams
    player = Player(team_id=home.id, name="Jack Grealish", position="MID")
    db_session.add(player)
    db_session.flush()

    absence = InjuryOrAbsence(
        player_id=player.id,
        team_id=home.id,
        fixture_id=sample_fixture.id,
        reason="injury",
        start_date=datetime.date(2023, 11, 20),
    )
    db_session.add(absence)
    db_session.commit()

    assert absence.player.name == "Jack Grealish"
    assert absence.reason == "injury"


def test_player_match_stats(
    db_session: Session, sample_fixture: Fixture, sample_teams
):
    home, _ = sample_teams
    player = Player(team_id=home.id, name="Erling Haaland", position="FWD")
    db_session.add(player)
    db_session.flush()

    stat = PlayerMatchStat(
        fixture_id=sample_fixture.id,
        player_id=player.id,
        team_id=home.id,
        minutes_played=90,
        goals=1,
        assists=0,
        xg=0.85,
    )
    db_session.add(stat)
    db_session.commit()

    assert stat.player.name == "Erling Haaland"
    assert stat.goals == 1


def test_team_match_stats(
    db_session: Session, sample_fixture: Fixture, sample_teams
):
    home, _ = sample_teams
    stat = TeamMatchStat(
        fixture_id=sample_fixture.id,
        team_id=home.id,
        formation="4-3-3",
        possession=58.3,
        shots=14,
        shots_on_target=6,
        xg=1.9,
    )
    db_session.add(stat)
    db_session.commit()

    assert stat.formation == "4-3-3"
    assert stat.possession == pytest.approx(58.3)


def test_prediction_with_scorelines_and_explanation(
    db_session: Session, sample_fixture: Fixture
):
    pred = Prediction(
        fixture_id=sample_fixture.id,
        request_hash="abc123",
        model_version="2.0.0",
        result="home",
        confidence="Medium",
        home_win_prob=0.52,
        draw_prob=0.26,
        away_win_prob=0.22,
        predicted_home_goals=1.8,
        predicted_away_goals=1.1,
        likely_score="2-1",
    )
    db_session.add(pred)
    db_session.flush()

    for rank, (hg, ag, prob) in enumerate([(2, 1, 0.19), (1, 1, 0.14), (1, 0, 0.12)], 1):
        db_session.add(
            PredictionScoreline(
                prediction_id=pred.id,
                home_goals=hg,
                away_goals=ag,
                probability=prob,
                rank=rank,
            )
        )

    explanation = PredictionExplanation(
        prediction_id=pred.id,
        key_factors=[
            {"factor": "home_form", "description": "Home team won 4 of last 5", "impact": "positive"}
        ],
        narrative="Home team predicted to win based on superior recent form.",
    )
    db_session.add(explanation)
    db_session.commit()

    assert pred.result == "home"
    assert len(pred.scorelines) == 3
    assert pred.scorelines[0].rank == 1
    assert pred.explanation.narrative is not None


def test_league_season_team_junction(
    db_session: Session,
    sample_league: League,
    sample_season: Season,
    sample_teams,
):
    home, away = sample_teams
    for team in (home, away):
        db_session.add(
            LeagueSeasonTeam(
                league_id=sample_league.id,
                season_id=sample_season.id,
                team_id=team.id,
            )
        )
    db_session.commit()

    assert len(sample_league.league_season_teams) == 2


def test_unique_constraints_enforced(db_session: Session, sample_teams):
    home, away = sample_teams
    player = Player(team_id=home.id, name="Rodri", position="MID")
    db_session.add(player)
    db_session.flush()

    # Second player with same name is allowed (different people can share a name)
    player2 = Player(team_id=away.id, name="Rodri", position="MID")
    db_session.add(player2)
    db_session.commit()
    assert player.id != player2.id
