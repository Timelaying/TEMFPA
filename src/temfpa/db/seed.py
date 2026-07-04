"""Database seeding script — populates leagues, seasons, and teams.

Run with:
    python -m temfpa.db.seed
"""

from __future__ import annotations

import datetime
import logging

from sqlalchemy.orm import Session

from temfpa.db.models import League, LeagueSeasonTeam, Season, Team
from temfpa.db.session import SessionLocal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static seed data
# ---------------------------------------------------------------------------

LEAGUES = [
    {"code": "EPL", "name": "Premier League", "country": "England", "tier": 1},
    {"code": "LA_LIGA", "name": "La Liga", "country": "Spain", "tier": 1},
    {"code": "BUNDESLIGA", "name": "Bundesliga", "country": "Germany", "tier": 1},
    {"code": "SERIE_A", "name": "Serie A", "country": "Italy", "tier": 1},
    {"code": "LIGUE_1", "name": "Ligue 1", "country": "France", "tier": 1},
    {"code": "UCL", "name": "UEFA Champions League", "country": "Europe", "tier": 1},
    {"code": "WORLD_CUP", "name": "FIFA World Cup", "country": "International", "tier": 1},
]

SEASONS = ["2022/2023", "2023/2024", "2024/2025"]
# World Cup uses its own season label
WC_SEASONS = ["2026"]

TEAMS_BY_LEAGUE: dict[str, list[dict]] = {
    "EPL": [
        {"name": "Arsenal", "short_name": "ARS", "country": "England"},
        {"name": "Aston Villa", "short_name": "AVL", "country": "England"},
        {"name": "Bournemouth", "short_name": "BOU", "country": "England"},
        {"name": "Brentford", "short_name": "BRE", "country": "England"},
        {"name": "Brighton & Hove Albion", "short_name": "BHA", "country": "England"},
        {"name": "Chelsea", "short_name": "CHE", "country": "England"},
        {"name": "Crystal Palace", "short_name": "CRY", "country": "England"},
        {"name": "Everton", "short_name": "EVE", "country": "England"},
        {"name": "Fulham", "short_name": "FUL", "country": "England"},
        {"name": "Ipswich Town", "short_name": "IPS", "country": "England"},
        {"name": "Leicester City", "short_name": "LEI", "country": "England"},
        {"name": "Liverpool", "short_name": "LIV", "country": "England"},
        {"name": "Manchester City", "short_name": "MCI", "country": "England"},
        {"name": "Manchester United", "short_name": "MUN", "country": "England"},
        {"name": "Newcastle United", "short_name": "NEW", "country": "England"},
        {"name": "Nottingham Forest", "short_name": "NFO", "country": "England"},
        {"name": "Southampton", "short_name": "SOU", "country": "England"},
        {"name": "Tottenham Hotspur", "short_name": "TOT", "country": "England"},
        {"name": "West Ham United", "short_name": "WHU", "country": "England"},
        {"name": "Wolverhampton Wanderers", "short_name": "WOL", "country": "England"},
    ],
    "LA_LIGA": [
        {"name": "Athletic Bilbao", "short_name": "ATH", "country": "Spain"},
        {"name": "Atletico Madrid", "short_name": "ATM", "country": "Spain"},
        {"name": "Barcelona", "short_name": "BAR", "country": "Spain"},
        {"name": "Betis", "short_name": "BET", "country": "Spain"},
        {"name": "Celta Vigo", "short_name": "CEL", "country": "Spain"},
        {"name": "Espanyol", "short_name": "ESP", "country": "Spain"},
        {"name": "Getafe", "short_name": "GET", "country": "Spain"},
        {"name": "Girona", "short_name": "GIR", "country": "Spain"},
        {"name": "Las Palmas", "short_name": "LPA", "country": "Spain"},
        {"name": "Leganes", "short_name": "LEG", "country": "Spain"},
        {"name": "Mallorca", "short_name": "MAL", "country": "Spain"},
        {"name": "Osasuna", "short_name": "OSA", "country": "Spain"},
        {"name": "Rayo Vallecano", "short_name": "RAY", "country": "Spain"},
        {"name": "Real Madrid", "short_name": "RMA", "country": "Spain"},
        {"name": "Real Sociedad", "short_name": "RSO", "country": "Spain"},
        {"name": "Real Valladolid", "short_name": "VAL", "country": "Spain"},
        {"name": "Sevilla", "short_name": "SEV", "country": "Spain"},
        {"name": "Valencia", "short_name": "VLC", "country": "Spain"},
        {"name": "Villarreal", "short_name": "VIL", "country": "Spain"},
        {"name": "Alaves", "short_name": "ALA", "country": "Spain"},
    ],
    "BUNDESLIGA": [
        {"name": "Augsburg", "short_name": "AUG", "country": "Germany"},
        {"name": "Bayern Munich", "short_name": "BAY", "country": "Germany"},
        {"name": "Bayer Leverkusen", "short_name": "LEV", "country": "Germany"},
        {"name": "Borussia Dortmund", "short_name": "BVB", "country": "Germany"},
        {"name": "Borussia Monchengladbach", "short_name": "BMG", "country": "Germany"},
        {"name": "Eintracht Frankfurt", "short_name": "SGE", "country": "Germany"},
        {"name": "Freiburg", "short_name": "SCF", "country": "Germany"},
        {"name": "Hamburger SV", "short_name": "HSV", "country": "Germany"},
        {"name": "Hoffenheim", "short_name": "TSG", "country": "Germany"},
        {"name": "Holstein Kiel", "short_name": "KIE", "country": "Germany"},
        {"name": "Mainz", "short_name": "M05", "country": "Germany"},
        {"name": "RB Leipzig", "short_name": "RBL", "country": "Germany"},
        {"name": "SC Freiburg", "short_name": "FRE", "country": "Germany"},
        {"name": "St. Pauli", "short_name": "STP", "country": "Germany"},
        {"name": "Stuttgart", "short_name": "VFB", "country": "Germany"},
        {"name": "Union Berlin", "short_name": "FCU", "country": "Germany"},
        {"name": "Werder Bremen", "short_name": "SVW", "country": "Germany"},
        {"name": "Wolfsburg", "short_name": "WOB", "country": "Germany"},
    ],
    "SERIE_A": [
        {"name": "AC Milan", "short_name": "MIL", "country": "Italy"},
        {"name": "Atalanta", "short_name": "ATA", "country": "Italy"},
        {"name": "Bologna", "short_name": "BOL", "country": "Italy"},
        {"name": "Cagliari", "short_name": "CAG", "country": "Italy"},
        {"name": "Como", "short_name": "COM", "country": "Italy"},
        {"name": "Empoli", "short_name": "EMP", "country": "Italy"},
        {"name": "Fiorentina", "short_name": "FIO", "country": "Italy"},
        {"name": "Genoa", "short_name": "GEN", "country": "Italy"},
        {"name": "Hellas Verona", "short_name": "HVE", "country": "Italy"},
        {"name": "Inter Milan", "short_name": "INT", "country": "Italy"},
        {"name": "Juventus", "short_name": "JUV", "country": "Italy"},
        {"name": "Lazio", "short_name": "LAZ", "country": "Italy"},
        {"name": "Lecce", "short_name": "LEC", "country": "Italy"},
        {"name": "Monza", "short_name": "MON", "country": "Italy"},
        {"name": "Napoli", "short_name": "NAP", "country": "Italy"},
        {"name": "Parma", "short_name": "PAR", "country": "Italy"},
        {"name": "Roma", "short_name": "ROM", "country": "Italy"},
        {"name": "Torino", "short_name": "TOR", "country": "Italy"},
        {"name": "Udinese", "short_name": "UDI", "country": "Italy"},
        {"name": "Venezia", "short_name": "VEN", "country": "Italy"},
    ],
    "LIGUE_1": [
        {"name": "Angers", "short_name": "ANG", "country": "France"},
        {"name": "Auxerre", "short_name": "AUX", "country": "France"},
        {"name": "Brest", "short_name": "BRE", "country": "France"},
        {"name": "Lens", "short_name": "LEN", "country": "France"},
        {"name": "Lille", "short_name": "LIL", "country": "France"},
        {"name": "Lyon", "short_name": "LYO", "country": "France"},
        {"name": "Marseille", "short_name": "OM", "country": "France"},
        {"name": "Monaco", "short_name": "MON", "country": "France"},
        {"name": "Montpellier", "short_name": "MTP", "country": "France"},
        {"name": "Nantes", "short_name": "NAN", "country": "France"},
        {"name": "Nice", "short_name": "NIC", "country": "France"},
        {"name": "Paris Saint-Germain", "short_name": "PSG", "country": "France"},
        {"name": "Reims", "short_name": "REI", "country": "France"},
        {"name": "Rennes", "short_name": "REN", "country": "France"},
        {"name": "Saint-Etienne", "short_name": "STE", "country": "France"},
        {"name": "Strasbourg", "short_name": "STR", "country": "France"},
        {"name": "Toulouse", "short_name": "TOU", "country": "France"},
        {"name": "Le Havre", "short_name": "HAV", "country": "France"},
    ],
    # Champions League — includes clubs from outside the Big 5 not seeded elsewhere
    "UCL": [
        # England (already in EPL seed, re-listed for UCL season links)
        {"name": "Arsenal", "short_name": "ARS", "country": "England"},
        {"name": "Aston Villa", "short_name": "AVL", "country": "England"},
        {"name": "Chelsea", "short_name": "CHE", "country": "England"},
        {"name": "Liverpool", "short_name": "LIV", "country": "England"},
        {"name": "Manchester City", "short_name": "MCI", "country": "England"},
        {"name": "Manchester United", "short_name": "MUN", "country": "England"},
        {"name": "Newcastle United", "short_name": "NEW", "country": "England"},
        {"name": "Tottenham Hotspur", "short_name": "TOT", "country": "England"},
        # Spain
        {"name": "Real Madrid", "short_name": "RMA", "country": "Spain"},
        {"name": "Barcelona", "short_name": "BAR", "country": "Spain"},
        {"name": "Atletico Madrid", "short_name": "ATM", "country": "Spain"},
        {"name": "Villarreal", "short_name": "VIL", "country": "Spain"},
        {"name": "Real Sociedad", "short_name": "RSO", "country": "Spain"},
        {"name": "Sevilla", "short_name": "SEV", "country": "Spain"},
        {"name": "Girona", "short_name": "GIR", "country": "Spain"},
        # Germany
        {"name": "Bayern Munich", "short_name": "BAY", "country": "Germany"},
        {"name": "Borussia Dortmund", "short_name": "BVB", "country": "Germany"},
        {"name": "RB Leipzig", "short_name": "RBL", "country": "Germany"},
        {"name": "Bayer Leverkusen", "short_name": "LEV", "country": "Germany"},
        {"name": "Eintracht Frankfurt", "short_name": "SGE", "country": "Germany"},
        {"name": "Stuttgart", "short_name": "VFB", "country": "Germany"},
        {"name": "Union Berlin", "short_name": "FCU", "country": "Germany"},
        # Italy
        {"name": "Inter Milan", "short_name": "INT", "country": "Italy"},
        {"name": "AC Milan", "short_name": "MIL", "country": "Italy"},
        {"name": "Juventus", "short_name": "JUV", "country": "Italy"},
        {"name": "Napoli", "short_name": "NAP", "country": "Italy"},
        {"name": "Atalanta", "short_name": "ATA", "country": "Italy"},
        {"name": "Lazio", "short_name": "LAZ", "country": "Italy"},
        {"name": "Roma", "short_name": "ROM", "country": "Italy"},
        {"name": "Bologna", "short_name": "BOL", "country": "Italy"},
        {"name": "Fiorentina", "short_name": "FIO", "country": "Italy"},
        # France
        {"name": "Paris Saint-Germain", "short_name": "PSG", "country": "France"},
        {"name": "Monaco", "short_name": "MON", "country": "France"},
        {"name": "Lille", "short_name": "LIL", "country": "France"},
        {"name": "Lens", "short_name": "LEN", "country": "France"},
        {"name": "Brest", "short_name": "BRE", "country": "France"},
        {"name": "Marseille", "short_name": "OM", "country": "France"},
        {"name": "Lyon", "short_name": "LYO", "country": "France"},
        # Portugal
        {"name": "Benfica", "short_name": "BEN", "country": "Portugal"},
        {"name": "Porto", "short_name": "POR", "country": "Portugal"},
        {"name": "Sporting CP", "short_name": "SCP", "country": "Portugal"},
        {"name": "Braga", "short_name": "SCB", "country": "Portugal"},
        # Netherlands
        {"name": "Ajax", "short_name": "AJX", "country": "Netherlands"},
        {"name": "PSV Eindhoven", "short_name": "PSV", "country": "Netherlands"},
        {"name": "Feyenoord", "short_name": "FEY", "country": "Netherlands"},
        {"name": "AZ Alkmaar", "short_name": "AZ", "country": "Netherlands"},
        # Scotland / Belgium / Turkey / Other
        {"name": "Celtic", "short_name": "CEL", "country": "Scotland"},
        {"name": "Rangers", "short_name": "RFC", "country": "Scotland"},
        {"name": "Club Brugge", "short_name": "BRU", "country": "Belgium"},
        {"name": "Anderlecht", "short_name": "AND", "country": "Belgium"},
        {"name": "Galatasaray", "short_name": "GAL", "country": "Turkey"},
        {"name": "Fenerbahce", "short_name": "FEN", "country": "Turkey"},
        {"name": "Besiktas", "short_name": "BJK", "country": "Turkey"},
        # Eastern Europe / Others
        {"name": "Shakhtar Donetsk", "short_name": "SHA", "country": "Ukraine"},
        {"name": "Dynamo Kyiv", "short_name": "DYN", "country": "Ukraine"},
        {"name": "Red Star Belgrade", "short_name": "RSB", "country": "Serbia"},
        {"name": "Sporting Lisbon", "short_name": "SPL", "country": "Portugal"},
        {"name": "Copenhagen", "short_name": "FCK", "country": "Denmark"},
        {"name": "Young Boys", "short_name": "YB", "country": "Switzerland"},
        {"name": "Red Bull Salzburg", "short_name": "RBS", "country": "Austria"},
        {"name": "Sturm Graz", "short_name": "STU", "country": "Austria"},
        {"name": "Slavia Prague", "short_name": "SLA", "country": "Czech Republic"},
        {"name": "GNK Dinamo Zagreb", "short_name": "DZG", "country": "Croatia"},
        {"name": "Antwerp", "short_name": "ANT", "country": "Belgium"},
    ],
    "WORLD_CUP": [
        {"name": "Algeria", "short_name": "ALG", "country": "Algeria"},
        {"name": "Argentina", "short_name": "ARG", "country": "Argentina"},
        {"name": "Australia", "short_name": "AUS", "country": "Australia"},
        {"name": "Austria", "short_name": "AUT", "country": "Austria"},
        {"name": "Belgium", "short_name": "BEL", "country": "Belgium"},
        {"name": "Bosnia-Herz", "short_name": "BIH", "country": "Bosnia and Herzegovina"},
        {"name": "Brazil", "short_name": "BRA", "country": "Brazil"},
        {"name": "Cabo Verde", "short_name": "CPV", "country": "Cape Verde"},
        {"name": "Canada", "short_name": "CAN", "country": "Canada"},
        {"name": "Colombia", "short_name": "COL", "country": "Colombia"},
        {"name": "Congo DR", "short_name": "COD", "country": "DR Congo"},
        {"name": "Croatia", "short_name": "CRO", "country": "Croatia"},
        {"name": "Curaçao", "short_name": "CUW", "country": "Curaçao"},
        {"name": "Czechia", "short_name": "CZE", "country": "Czech Republic"},
        {"name": "Côte d'Ivoire", "short_name": "CIV", "country": "Ivory Coast"},
        {"name": "Ecuador", "short_name": "ECU", "country": "Ecuador"},
        {"name": "Egypt", "short_name": "EGY", "country": "Egypt"},
        {"name": "England", "short_name": "ENG", "country": "England"},
        {"name": "France", "short_name": "FRA", "country": "France"},
        {"name": "Germany", "short_name": "GER", "country": "Germany"},
        {"name": "Ghana", "short_name": "GHA", "country": "Ghana"},
        {"name": "Haiti", "short_name": "HAI", "country": "Haiti"},
        {"name": "IR Iran", "short_name": "IRN", "country": "Iran"},
        {"name": "Iraq", "short_name": "IRQ", "country": "Iraq"},
        {"name": "Japan", "short_name": "JPN", "country": "Japan"},
        {"name": "Jordan", "short_name": "JOR", "country": "Jordan"},
        {"name": "Korea Republic", "short_name": "KOR", "country": "South Korea"},
        {"name": "Mexico", "short_name": "MEX", "country": "Mexico"},
        {"name": "Morocco", "short_name": "MAR", "country": "Morocco"},
        {"name": "Netherlands", "short_name": "NED", "country": "Netherlands"},
        {"name": "New Zealand", "short_name": "NZL", "country": "New Zealand"},
        {"name": "Norway", "short_name": "NOR", "country": "Norway"},
        {"name": "Panama", "short_name": "PAN", "country": "Panama"},
        {"name": "Paraguay", "short_name": "PAR", "country": "Paraguay"},
        {"name": "Portugal", "short_name": "POR", "country": "Portugal"},
        {"name": "Qatar", "short_name": "QAT", "country": "Qatar"},
        {"name": "Saudi Arabia", "short_name": "KSA", "country": "Saudi Arabia"},
        {"name": "Scotland", "short_name": "SCO", "country": "Scotland"},
        {"name": "Senegal", "short_name": "SEN", "country": "Senegal"},
        {"name": "South Africa", "short_name": "RSA", "country": "South Africa"},
        {"name": "Spain", "short_name": "ESP", "country": "Spain"},
        {"name": "Sweden", "short_name": "SWE", "country": "Sweden"},
        {"name": "Switzerland", "short_name": "SUI", "country": "Switzerland"},
        {"name": "Tunisia", "short_name": "TUN", "country": "Tunisia"},
        {"name": "Türkiye", "short_name": "TUR", "country": "Turkey"},
        {"name": "United States", "short_name": "USA", "country": "United States"},
        {"name": "Uruguay", "short_name": "URU", "country": "Uruguay"},
        {"name": "Uzbekistan", "short_name": "UZB", "country": "Uzbekistan"},
    ],
}


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------


def seed_database(db: Session, verbose: bool = True) -> dict:
    """Seed leagues, seasons, teams, and LeagueSeasonTeam links.

    Returns a summary dict with counts.
    """
    counts = {"leagues": 0, "seasons": 0, "teams": 0, "links": 0}

    league_map: dict[str, League] = {}

    # 1. Leagues
    for lg_data in LEAGUES:
        existing = db.query(League).filter_by(code=lg_data["code"]).first()
        if existing:
            league_map[lg_data["code"]] = existing
        else:
            lg = League(**lg_data)
            db.add(lg)
            db.flush()
            league_map[lg_data["code"]] = lg
            counts["leagues"] += 1
            if verbose:
                logger.info("Created league: %s", lg_data["name"])

    # 2. Seasons — one per league per label
    season_map: dict[tuple[str, str], Season] = {}

    def _ensure_season(code: str, league: League, season_label: str, start: datetime.date, end: datetime.date):
        key = (code, season_label)
        existing = db.query(Season).filter_by(league_id=league.id, label=season_label).first()
        if existing:
            season_map[key] = existing
        else:
            s = Season(league_id=league.id, label=season_label, start_date=start, end_date=end)
            db.add(s)
            db.flush()
            season_map[key] = s
            counts["seasons"] += 1

    for season_label in SEASONS:
        try:
            start_year = int(season_label.split("/")[0])
        except (ValueError, IndexError):
            start_year = 2023
        for code, league in league_map.items():
            if code in ("WORLD_CUP",):
                continue  # handled separately
            _ensure_season(code, league, season_label,
                           datetime.date(start_year, 8, 1),
                           datetime.date(start_year + 1, 6, 30))

    # World Cup uses its own season labels (just the year)
    if "WORLD_CUP" in league_map:
        wc_league = league_map["WORLD_CUP"]
        for wc_label in WC_SEASONS:
            year = int(wc_label)
            _ensure_season("WORLD_CUP", wc_league, wc_label,
                           datetime.date(year, 6, 1),
                           datetime.date(year, 7, 31))

    # 3. Teams + LeagueSeasonTeam links
    for league_code, team_list in TEAMS_BY_LEAGUE.items():
        league = league_map.get(league_code)
        if not league:
            continue

        for t_data in team_list:
            # Find or create Team
            existing_team = db.query(Team).filter_by(name=t_data["name"]).first()
            if existing_team:
                team = existing_team
            else:
                team = Team(**t_data)
                db.add(team)
                db.flush()
                counts["teams"] += 1
                if verbose:
                    logger.info("Created team: %s", t_data["name"])

            # Link to all seasons (WC uses its own labels)
            labels = WC_SEASONS if league_code == "WORLD_CUP" else SEASONS
            for season_label in labels:
                season = season_map.get((league_code, season_label))
                if not season:
                    continue
                existing_link = db.query(LeagueSeasonTeam).filter_by(
                    league_id=league.id,
                    season_id=season.id,
                    team_id=team.id,
                ).first()
                if not existing_link:
                    db.add(LeagueSeasonTeam(
                        league_id=league.id,
                        season_id=season.id,
                        team_id=team.id,
                    ))
                    counts["links"] += 1

    db.commit()
    if verbose:
        logger.info(
            "Seed complete: %d leagues, %d seasons, %d teams, %d links",
            counts["leagues"], counts["seasons"], counts["teams"], counts["links"],
        )
    return counts


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    db = SessionLocal()
    try:
        summary = seed_database(db)
        print(f"Seed done: {summary}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
