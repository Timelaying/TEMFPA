"""Command-line interface for TEMFPA data retrieval."""

from __future__ import annotations

import argparse
import logging

from temfpa.retrieval import get_match_results, get_team_position

logger = logging.getLogger(__name__)


def parse_seasons(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TEMFPA football data CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    positions = subparsers.add_parser("positions", help="Get team position by season")
    positions.add_argument("team", help="Team name, e.g. 'Manchester City'")
    positions.add_argument(
        "--seasons",
        default="2023/2024",
        help="Comma-separated seasons, e.g. '2023/2024,2022/2023'",
    )
    positions.add_argument("--league", default="ENG-Premier League")
    positions.add_argument(
        "--cache-dir",
        default=None,
        help="Optional cache directory. Defaults to $TEMFPA_CACHE_DIR or ~/.cache/temfpa",
    )
    positions.add_argument(
        "--offline",
        action="store_true",
        help="Use cached data only and skip external FotMob fetches.",
    )

    matches = subparsers.add_parser("matches", help="Get head-to-head match results")
    matches.add_argument("team1")
    matches.add_argument("team2")
    matches.add_argument(
        "--seasons",
        default="2023/2024",
        help="Comma-separated seasons, e.g. '2023/2024,2022/2023'",
    )
    matches.add_argument("--league", default="ENG-Premier League")
    matches.add_argument(
        "--cache-dir",
        default=None,
        help="Optional cache directory. Defaults to $TEMFPA_CACHE_DIR or ~/.cache/temfpa",
    )
    matches.add_argument(
        "--offline",
        action="store_true",
        help="Use cached data only and skip external FotMob fetches.",
    )

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    parser = build_parser()
    args = parser.parse_args()
    seasons = parse_seasons(args.seasons)

    if args.command == "positions":
        df = get_team_position(
            args.team,
            leagues=args.league,
            seasons=seasons,
            cache_dir=args.cache_dir,
            offline=args.offline,
        )
    else:
        df = get_match_results(
            args.team1,
            args.team2,
            leagues=args.league,
            seasons=seasons,
            cache_dir=args.cache_dir,
            offline=args.offline,
        )

    if df.empty:
        logger.warning("No data found for the provided input.")
        return

    logger.info("Retrieved %s records.", len(df))
    logger.info("\n%s", df.to_string(index=False))


if __name__ == "__main__":
    main()
