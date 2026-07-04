"""Data sync script — populates the database from the ingestion router.

Usage:
    python -m temfpa.ingestion.sync --league EPL --season "2023/2024"
    python -m temfpa.ingestion.sync --league EPL --season "2023/2024" --skip-lineups
"""

from __future__ import annotations

import argparse
import datetime
import logging
import sys

from sqlalchemy.orm import Session

from temfpa.db.models import (
    Fixture,
    InjuryOrAbsence,
    League,
    Lineup,
    LineupPlayer,
    MatchResult,
    Player,
    PlayerMatchStat,
    Season,
    Team,
    TeamMatchStat,
)
from temfpa.db.session import SessionLocal
from temfpa.ingestion.base import (
    FixtureDTO,
    LineupDTO,
    MatchResultDTO,
    PlayerMatchStatDTO,
    TeamMatchStatDTO,
)
from temfpa.db.prediction_log_service import resolve_predictions
from temfpa.ingestion.router import IngestionRouter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Upsert helpers — find-or-create by name/code so we get stable IDs
# ---------------------------------------------------------------------------


def _get_or_create_league(db: Session, code: str, name: str = "", country: str = "") -> League:
    league = db.query(League).filter_by(code=code).first()
    if not league:
        league = League(code=code, name=name or code, country=country or "Unknown", tier=1)
        db.add(league)
        db.flush()
    return league


def _get_or_create_season(db: Session, league: League, label: str) -> Season:
    season = db.query(Season).filter_by(league_id=league.id, label=label).first()
    if not season:
        try:
            parts = label.split("/")
            if len(parts) == 2:
                # Standard "2023/2024" format — domestic league
                start_year = int(parts[0])
                start = datetime.date(start_year, 8, 1)
                end = datetime.date(start_year + 1, 6, 30)
            else:
                # Plain year e.g. "2026" — World Cup / tournament
                year = int(label)
                start = datetime.date(year, 6, 1)
                end = datetime.date(year, 7, 31)
        except (ValueError, IndexError):
            year = datetime.date.today().year
            start = datetime.date(year, 8, 1)
            end = datetime.date(year + 1, 6, 30)
        season = Season(league_id=league.id, label=label, start_date=start, end_date=end)
        db.add(season)
        db.flush()
    return season


def _normalise_team_name(name: str) -> str:
    """Collapse common name variants to a canonical form."""
    aliases: dict[str, str] = {
        # EPL
        "Man United": "Manchester United",
        "Man Utd": "Manchester United",
        "Manchester Utd": "Manchester United",
        "Man City": "Manchester City",
        "Wolves": "Wolverhampton Wanderers",
        "Spurs": "Tottenham Hotspur",
        "Tottenham": "Tottenham Hotspur",
        "Leeds": "Leeds United",
        "Newcastle": "Newcastle United",
        "Brighton": "Brighton & Hove Albion",
        "West Ham": "West Ham United",
        "Leicester": "Leicester City",
        "Nottingham": "Nottingham Forest",
        "Nott'm Forest": "Nottingham Forest",
        # World Cup national teams
        "USA": "United States",
        "South Korea": "Korea Republic",
        "Ivory Coast": "Côte d'Ivoire",
        "Bosnia & Herzegovina": "Bosnia-Herz",
        "Bosnia–Herz": "Bosnia-Herz",
        "DR Congo": "Congo DR",
        "Iran": "IR Iran",
        "Turkey": "Türkiye",
    }
    return aliases.get(name.strip(), name.strip())


def _get_or_create_team(db: Session, name: str) -> Team:
    canonical = _normalise_team_name(name)
    team = db.query(Team).filter_by(name=canonical).first()
    if not team:
        team = Team(name=canonical)
        db.add(team)
        db.flush()
    return team


def _get_or_create_player(db: Session, name: str, team: Team) -> Player:
    player = (
        db.query(Player)
        .filter_by(name=name, team_id=team.id)
        .first()
    )
    if not player:
        player = Player(name=name, team_id=team.id)
        db.add(player)
        db.flush()
    return player


def _find_fixture(
    db: Session,
    season: Season,
    home_team: Team,
    away_team: Team,
    fixture_date: datetime.datetime,
) -> Fixture | None:
    # Match within a ±1-day window to handle timezone differences
    date_from = fixture_date - datetime.timedelta(days=1)
    date_to = fixture_date + datetime.timedelta(days=1)
    return (
        db.query(Fixture)
        .filter(
            Fixture.season_id == season.id,
            Fixture.home_team_id == home_team.id,
            Fixture.away_team_id == away_team.id,
            Fixture.fixture_date >= date_from,
            Fixture.fixture_date <= date_to,
        )
        .first()
    )


# ---------------------------------------------------------------------------
# Sync functions
# ---------------------------------------------------------------------------


def sync_fixtures(
    db: Session,
    router: IngestionRouter,
    league_code: str,
    season_label: str,
) -> int:
    """Upsert fixtures into the database. Returns count of new fixtures."""
    league = _get_or_create_league(db, league_code)
    season = _get_or_create_season(db, league, season_label)

    dtos = router.fetch_fixtures(league_code, season_label)
    new_count = 0
    for dto in dtos:
        home = _get_or_create_team(db, dto.home_team_name)
        away = _get_or_create_team(db, dto.away_team_name)

        existing = _find_fixture(db, season, home, away, dto.fixture_date)
        if existing:
            existing.status = dto.status
            if dto.venue:
                existing.venue = dto.venue
            if dto.matchweek:
                existing.matchweek = dto.matchweek
        else:
            fixture = Fixture(
                season_id=season.id,
                home_team_id=home.id,
                away_team_id=away.id,
                fixture_date=dto.fixture_date,
                venue=dto.venue,
                status=dto.status,
                matchweek=dto.matchweek,
                provider_ids=dto.provider_ids,
            )
            db.add(fixture)
            new_count += 1

    db.commit()
    logger.info("sync_fixtures: %d new fixtures for %s %s", new_count, league_code, season_label)
    return new_count


def sync_results(
    db: Session,
    router: IngestionRouter,
    league_code: str,
    season_label: str,
) -> int:
    """Upsert match results. Returns count of new/updated results."""
    league = _get_or_create_league(db, league_code)
    season = _get_or_create_season(db, league, season_label)

    dtos = router.fetch_results(league_code, season_label)
    updated = 0
    for dto in dtos:
        home = _get_or_create_team(db, dto.home_team_name)
        away = _get_or_create_team(db, dto.away_team_name)

        fixture = _find_fixture(db, season, home, away, dto.fixture_date)
        if not fixture:
            fixture = Fixture(
                season_id=season.id,
                home_team_id=home.id,
                away_team_id=away.id,
                fixture_date=dto.fixture_date,
                status="FINISHED",
            )
            db.add(fixture)
            db.flush()

        fixture.status = "FINISHED"

        if dto.home_goals is not None and dto.away_goals is not None:
            winner = (
                "home" if dto.home_goals > dto.away_goals
                else "away" if dto.away_goals > dto.home_goals
                else "draw"
            )
            existing_result = (
                db.query(MatchResult).filter_by(fixture_id=fixture.id).first()
            )
            if existing_result:
                existing_result.home_goals = dto.home_goals
                existing_result.away_goals = dto.away_goals
                existing_result.winner = winner
                existing_result.home_xg = dto.home_xg
                existing_result.away_xg = dto.away_xg
            else:
                db.add(
                    MatchResult(
                        fixture_id=fixture.id,
                        home_goals=dto.home_goals,
                        away_goals=dto.away_goals,
                        home_ht_goals=dto.home_ht_goals,
                        away_ht_goals=dto.away_ht_goals,
                        winner=winner,
                        home_xg=dto.home_xg,
                        away_xg=dto.away_xg,
                    )
                )
            updated += 1

    db.commit()
    logger.info("sync_results: %d results for %s %s", updated, league_code, season_label)

    # Resolve any pending prediction logs now that results are in
    try:
        resolve_predictions(db)
    except Exception:
        logger.warning("resolve_predictions failed; skipping", exc_info=True)

    return updated


def sync_lineups(
    db: Session,
    router: IngestionRouter,
    league_code: str,
    season_label: str,
) -> int:
    league = _get_or_create_league(db, league_code)
    season = _get_or_create_season(db, league, season_label)

    dtos = router.fetch_lineups(league_code, season_label)
    new_count = 0
    for dto in dtos:
        home = _get_or_create_team(db, dto.home_team_name)
        away = _get_or_create_team(db, dto.away_team_name)
        team = _get_or_create_team(db, dto.team_name)

        fixture = _find_fixture(db, season, home, away, dto.fixture_date)
        if not fixture:
            continue

        existing = (
            db.query(Lineup)
            .filter_by(fixture_id=fixture.id, team_id=team.id)
            .first()
        )
        if existing:
            if dto.formation:
                existing.formation = dto.formation
            continue

        lineup = Lineup(
            fixture_id=fixture.id,
            team_id=team.id,
            formation=dto.formation,
            is_confirmed=dto.is_confirmed,
        )
        db.add(lineup)
        db.flush()

        for pname in dto.starters:
            player = _get_or_create_player(db, pname, team)
            if not db.query(LineupPlayer).filter_by(lineup_id=lineup.id, player_id=player.id).first():
                db.add(LineupPlayer(lineup_id=lineup.id, player_id=player.id, is_starter=True))

        for pname in dto.substitutes:
            player = _get_or_create_player(db, pname, team)
            if not db.query(LineupPlayer).filter_by(lineup_id=lineup.id, player_id=player.id).first():
                db.add(LineupPlayer(lineup_id=lineup.id, player_id=player.id, is_starter=False))

        new_count += 1

    db.commit()
    logger.info("sync_lineups: %d lineups for %s %s", new_count, league_code, season_label)
    return new_count


def sync_player_stats(
    db: Session,
    router: IngestionRouter,
    league_code: str,
    season_label: str,
) -> int:
    league = _get_or_create_league(db, league_code)
    season = _get_or_create_season(db, league, season_label)

    dtos = router.fetch_player_stats(league_code, season_label)
    new_count = 0
    for dto in dtos:
        home = _get_or_create_team(db, dto.home_team_name)
        away = _get_or_create_team(db, dto.away_team_name)
        team = _get_or_create_team(db, dto.team_name)

        fixture = _find_fixture(db, season, home, away, dto.fixture_date)
        if not fixture:
            continue

        player = _get_or_create_player(db, dto.player_name, team)

        existing = (
            db.query(PlayerMatchStat)
            .filter_by(fixture_id=fixture.id, player_id=player.id)
            .first()
        )
        if existing:
            continue

        db.add(
            PlayerMatchStat(
                fixture_id=fixture.id,
                player_id=player.id,
                team_id=team.id,
                minutes_played=dto.minutes_played,
                goals=dto.goals,
                assists=dto.assists,
                yellow_cards=dto.yellow_cards,
                red_cards=dto.red_cards,
                xg=dto.xg,
                xa=dto.xa,
            )
        )
        new_count += 1

    db.commit()
    logger.info("sync_player_stats: %d records for %s %s", new_count, league_code, season_label)
    return new_count


def sync_team_stats(
    db: Session,
    router: IngestionRouter,
    league_code: str,
    season_label: str,
) -> int:
    league = _get_or_create_league(db, league_code)
    season = _get_or_create_season(db, league, season_label)

    dtos = router.fetch_team_stats(league_code, season_label)
    new_count = 0
    for dto in dtos:
        home = _get_or_create_team(db, dto.home_team_name)
        away = _get_or_create_team(db, dto.away_team_name)
        team = _get_or_create_team(db, dto.team_name)

        fixture = _find_fixture(db, season, home, away, dto.fixture_date)
        if not fixture:
            continue

        existing = (
            db.query(TeamMatchStat)
            .filter_by(fixture_id=fixture.id, team_id=team.id)
            .first()
        )
        if not existing:
            db.add(
                TeamMatchStat(
                    fixture_id=fixture.id,
                    team_id=team.id,
                    formation=dto.formation,
                    possession=dto.possession,
                    shots=dto.shots,
                    shots_on_target=dto.shots_on_target,
                    xg=dto.xg,
                )
            )
            new_count += 1

    db.commit()
    logger.info("sync_team_stats: %d records for %s %s", new_count, league_code, season_label)
    return new_count


def run_full_sync(
    league_code: str,
    season_label: str,
    skip_lineups: bool = False,
    skip_player_stats: bool = False,
) -> None:
    router = IngestionRouter()
    db = SessionLocal()
    try:
        sync_fixtures(db, router, league_code, season_label)
        sync_results(db, router, league_code, season_label)
        if not skip_lineups:
            sync_lineups(db, router, league_code, season_label)
        if not skip_player_stats:
            sync_player_stats(db, router, league_code, season_label)
        sync_team_stats(db, router, league_code, season_label)
        logger.info("Full sync complete for %s %s", league_code, season_label)
    finally:
        db.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="TEMFPA data sync")
    parser.add_argument("--league", required=True, help="League code, e.g. EPL")
    parser.add_argument("--season", required=True, help='Season label, e.g. "2023/2024"')
    parser.add_argument("--skip-lineups", action="store_true")
    parser.add_argument("--skip-player-stats", action="store_true")
    args = parser.parse_args()

    run_full_sync(
        args.league,
        args.season,
        skip_lineups=args.skip_lineups,
        skip_player_stats=args.skip_player_stats,
    )


if __name__ == "__main__":
    main()
