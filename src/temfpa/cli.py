"""Command-line interface for TEMFPA data retrieval."""

from __future__ import annotations

import argparse

from temfpa.retrieval import get_match_results, get_team_position


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

    matches = subparsers.add_parser("matches", help="Get head-to-head match results")
    matches.add_argument("team1")
    matches.add_argument("team2")
    matches.add_argument(
        "--seasons",
        default="2023/2024",
        help="Comma-separated seasons, e.g. '2023/2024,2022/2023'",
    )
    matches.add_argument("--league", default="ENG-Premier League")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    seasons = parse_seasons(args.seasons)

    if args.command == "positions":
        df = get_team_position(args.team, leagues=args.league, seasons=seasons)
    else:
        df = get_match_results(args.team1, args.team2, leagues=args.league, seasons=seasons)

    if df.empty:
        print("No data found for the provided input.")
        return

    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
