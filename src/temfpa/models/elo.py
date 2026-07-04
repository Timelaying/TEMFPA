"""Elo rating system for team strength estimation."""

from __future__ import annotations

import math
from typing import Optional


# ---------------------------------------------------------------------------
# Prior ratings — approximate Elo equivalents based on recent performance.
# Used when no match history exists for a team so predictions are meaningful
# even with an empty database.  Values calibrated to top-league averages.
# ---------------------------------------------------------------------------

PRIOR_RATINGS: dict[str, float] = {
    # EPL 2024/25 approximate strengths
    "Liverpool": 1740,
    "Manchester City": 1720,
    "Arsenal": 1700,
    "Aston Villa": 1610,
    "Chelsea": 1590,
    "Tottenham Hotspur": 1545,
    "Newcastle United": 1530,
    "Brighton & Hove Albion": 1490,
    "Nottingham Forest": 1470,
    "Bournemouth": 1455,
    "Fulham": 1450,
    "Crystal Palace": 1440,
    "Brentford": 1435,
    "West Ham United": 1430,
    "Manchester United": 1420,
    "Everton": 1410,
    "Wolverhampton Wanderers": 1400,
    "Ipswich Town": 1355,
    "Leicester City": 1345,
    "Southampton": 1300,
    # La Liga approximate strengths
    "Real Madrid": 1780,
    "Barcelona": 1730,
    "Atletico Madrid": 1680,
    "Athletic Bilbao": 1560,
    "Real Sociedad": 1540,
    "Villarreal": 1520,
    "Betis": 1490,
    "Sevilla": 1480,
    "Valencia": 1430,
    "Osasuna": 1420,
    "Celta Vigo": 1410,
    "Girona": 1460,
    "Rayo Vallecano": 1390,
    "Mallorca": 1380,
    "Getafe": 1370,
    "Leganes": 1340,
    "Real Valladolid": 1330,
    "Las Palmas": 1320,
    "Espanyol": 1310,
    "Alaves": 1360,
    # Bundesliga
    "Bayern Munich": 1760,
    "Bayer Leverkusen": 1700,
    "Borussia Dortmund": 1640,
    "RB Leipzig": 1620,
    "Eintracht Frankfurt": 1560,
    "Stuttgart": 1540,
    "Freiburg": 1510,
    "SC Freiburg": 1510,
    "Hoffenheim": 1480,
    "Werder Bremen": 1460,
    "Mainz": 1450,
    "Augsburg": 1430,
    "Borussia Monchengladbach": 1440,
    "Union Berlin": 1400,
    "Wolfsburg": 1390,
    "St. Pauli": 1360,
    "Holstein Kiel": 1330,
    "Hamburger SV": 1340,
    # Serie A
    "Inter Milan": 1720,
    "AC Milan": 1680,
    "Juventus": 1660,
    "Napoli": 1640,
    "Atalanta": 1650,
    "Lazio": 1560,
    "Roma": 1550,
    "Fiorentina": 1520,
    "Bologna": 1490,
    "Torino": 1450,
    "Monza": 1420,
    "Genoa": 1410,
    "Udinese": 1400,
    "Cagliari": 1390,
    "Lecce": 1370,
    "Empoli": 1360,
    "Hellas Verona": 1340,
    "Como": 1320,
    "Parma": 1310,
    "Venezia": 1300,
    # Ligue 1
    "Paris Saint-Germain": 1780,
    "Monaco": 1620,
    "Lille": 1590,
    "Lyon": 1560,
    "Nice": 1540,
    "Marseille": 1530,
    "Lens": 1510,
    "Rennes": 1490,
    "Strasbourg": 1450,
    "Toulouse": 1430,
    "Brest": 1420,
    "Reims": 1410,
    "Nantes": 1400,
    "Montpellier": 1380,
    "Auxerre": 1360,
    "Angers": 1340,
    "Saint-Etienne": 1320,
    "Le Havre": 1350,
    # Champions League — calibrated to club-elo.com ratings, scaled to match system baseline.
    # Big-5 teams inherit their domestic ratings above; non-Big-5 entries below.
    "Benfica": 1660,
    "Porto": 1640,
    "Sporting CP": 1620,
    "Sporting Lisbon": 1620,
    "Braga": 1530,
    "Ajax": 1640,
    "PSV Eindhoven": 1630,
    "Feyenoord": 1610,
    "AZ Alkmaar": 1550,
    "Celtic": 1570,
    "Rangers": 1530,
    "Club Brugge": 1570,
    "Anderlecht": 1510,
    "Antwerp": 1490,
    "Galatasaray": 1580,
    "Fenerbahce": 1550,
    "Besiktas": 1510,
    "Shakhtar Donetsk": 1580,
    "Dynamo Kyiv": 1490,
    "Red Star Belgrade": 1540,
    "Copenhagen": 1510,
    "Young Boys": 1480,
    "Red Bull Salzburg": 1540,
    "Sturm Graz": 1450,
    "Slavia Prague": 1500,
    "GNK Dinamo Zagreb": 1490,
    # -----------------------------------------------------------------------
    # FIFA World Cup 2026 — national team Elo equivalents based on
    # FIFA world rankings (rank 1 ≈ 2100, scaled to system baseline 1500).
    # Formula: rating ≈ 2100 - (rank - 1) * 12, floored at 1300.
    # -----------------------------------------------------------------------
    "France": 2040,
    "Spain": 2030,
    "Brazil": 2010,
    "England": 2000,
    "Argentina": 2000,
    "Portugal": 1980,
    "Germany": 1970,
    "Netherlands": 1950,
    "Belgium": 1930,
    "Croatia": 1900,
    "Uruguay": 1880,
    "United States": 1870,
    "Mexico": 1860,
    "Colombia": 1850,
    "Japan": 1840,
    "Morocco": 1830,
    "Switzerland": 1820,
    "Senegal": 1810,
    "Australia": 1790,
    "Norway": 1780,
    "Canada": 1770,
    "Ecuador": 1760,
    "South Korea": 1750,
    "Korea Republic": 1750,
    "Sweden": 1740,
    "Türkiye": 1730,
    "Austria": 1720,
    "Czechia": 1710,
    "Poland": 1700,
    "Scotland": 1690,
    "Algeria": 1680,
    "Côte d'Ivoire": 1670,
    "Tunisia": 1660,
    "Egypt": 1650,
    "Paraguay": 1640,
    "Ghana": 1630,
    "Uzbekistan": 1620,
    "Bolivia": 1600,
    "Saudi Arabia": 1590,
    "Panama": 1580,
    "Qatar": 1570,
    "Iraq": 1560,
    "IR Iran": 1550,
    "Jordan": 1540,
    "New Zealand": 1520,
    "Cabo Verde": 1510,
    "Congo DR": 1500,
    "South Africa": 1490,
    "Haiti": 1460,
    "Curaçao": 1440,
    "Bosnia-Herz": 1700,
}


# Empirically calibrated home advantage per league (in Elo points).
# Lower = weaker home effect. World Cup / UCL group stages = neutral or near-neutral.
HOME_ADVANTAGE_BY_LEAGUE: dict[str, float] = {
    "EPL": 55.0,
    "LA_LIGA": 110.0,
    "BUNDESLIGA": 55.0,
    "SERIE_A": 90.0,
    "LIGUE_1": 75.0,
    "UCL": 30.0,
    "WORLD_CUP": 0.0,
}


class EloRating:
    """Elo rating system for football teams."""

    # Home advantage expressed in Elo points.  Empirically, home teams in
    # top European leagues perform as if they are ~100 Elo points stronger.
    HOME_ADVANTAGE: float = 100.0

    def __init__(self, k: float = 30, base_rating: float = 1500) -> None:
        self.k = k
        self.base_rating = base_rating
        self._ratings: dict[int, float] = {}
        self._names: dict[int, str] = {}   # team_id → canonical name

    def get_rating(self, team_id: int) -> float:
        """Return current Elo rating for a team.

        Falls back to PRIOR_RATINGS by team name, then to base_rating.
        """
        if team_id in self._ratings:
            return self._ratings[team_id]
        # Try prior by name
        name = self._names.get(team_id)
        if name and name in PRIOR_RATINGS:
            return PRIOR_RATINGS[name]
        return self.base_rating

    def _expected(self, rating_a: float, rating_b: float) -> float:
        """Expected score for team A given two ratings (logistic formula)."""
        return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))

    def update(self, home_team_id: int, away_team_id: int, result: str, k_override: float | None = None) -> None:
        """Update Elo ratings after a match."""
        home_rating = self.get_rating(home_team_id)
        away_rating = self.get_rating(away_team_id)

        expected_home = self._expected(home_rating, away_rating)
        expected_away = 1.0 - expected_home
        k = k_override if k_override is not None else self.k

        if result == "home":
            actual_home, actual_away = 1.0, 0.0
        elif result == "away":
            actual_home, actual_away = 0.0, 1.0
        else:
            actual_home, actual_away = 0.5, 0.5

        self._ratings[home_team_id] = home_rating + k * (actual_home - expected_home)
        self._ratings[away_team_id] = away_rating + k * (actual_away - expected_away)

    def expected_home_win_prob(
        self, home_team_id: int, away_team_id: int, league_code: str | None = None
    ) -> tuple[float, float, float]:
        """Return (home_win_prob, draw_prob, away_win_prob).

        Home advantage of +100 Elo points is applied to the home team.
        """
        adv = HOME_ADVANTAGE_BY_LEAGUE.get(league_code, self.HOME_ADVANTAGE) if league_code else self.HOME_ADVANTAGE
        home_rating = self.get_rating(home_team_id) + adv
        away_rating = self.get_rating(away_team_id)

        raw_home = self._expected(home_rating, away_rating)
        raw_away = 1.0 - raw_home

        draw_prob = 0.25 * (1.0 - abs(raw_home - raw_away))
        draw_prob = max(0.0, min(1.0, draw_prob))

        remaining = 1.0 - draw_prob
        home_win_prob = raw_home * remaining
        away_win_prob = raw_away * remaining

        total = home_win_prob + draw_prob + away_win_prob
        if total > 0:
            home_win_prob /= total
            draw_prob /= total
            away_win_prob /= total

        return home_win_prob, draw_prob, away_win_prob

    @classmethod
    def build_from_db(
        cls,
        db,
        league_id: Optional[int] = None,
        before_date=None,
        k: float = 30,
        base_rating: float = 1500,
    ) -> "EloRating":
        """Build Elo ratings by replaying all MatchResults chronologically.

        Team names are loaded so that PRIOR_RATINGS can be used for
        teams with no match history.
        """
        from temfpa.db.models import Fixture, MatchResult, Season, Team

        elo = cls(k=k, base_rating=base_rating)

        # Load team names for prior-rating lookups
        for team in db.query(Team).all():
            elo._names[team.id] = team.name

        query = (
            db.query(Fixture, MatchResult)
            .join(MatchResult, MatchResult.fixture_id == Fixture.id)
            .filter(
                Fixture.status == "FINISHED",
                MatchResult.winner.isnot(None),
            )
        )

        if league_id is not None:
            query = query.join(Season, Season.id == Fixture.season_id).filter(
                Season.league_id == league_id
            )

        if before_date is not None:
            import datetime
            if isinstance(before_date, datetime.date) and not isinstance(before_date, datetime.datetime):
                before_date = datetime.datetime.combine(before_date, datetime.time.max)
            query = query.filter(Fixture.fixture_date < before_date)

        rows = query.order_by(Fixture.fixture_date.asc()).all()

        today = datetime.date.today()
        for fixture, result in rows:
            fixture_day = fixture.fixture_date.date() if hasattr(fixture.fixture_date, 'date') else fixture.fixture_date
            days_old = max(0, (today - fixture_day).days)
            # K decays exponentially: half-life ~2.3 years (decay=0.3)
            k_effective = k * math.exp(-0.3 * days_old / 365)
            elo.update(fixture.home_team_id, fixture.away_team_id, result.winner, k_override=k_effective)

        return elo
