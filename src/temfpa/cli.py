"""Command-line interface for TEMFPA data retrieval."""

from __future__ import annotations

import argparse
import logging

from temfpa.analytics import (
    batch_head_to_head,
    export_results,
    plot_head_to_head_goals,
    predict_match_outcomes,
)
from temfpa.retrieval import get_match_results, get_team_position

logger = logging.getLogger(__name__)


def parse_seasons(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def parse_pairs(raw: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for part in raw.split(";"):
        if "|" not in part:
            continue
        t1, t2 = part.split("|", 1)
        pairs.append((t1.strip(), t2.strip()))
    return pairs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TEMFPA football data CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    positions = subparsers.add_parser("positions", help="Get team position by season")
    positions.add_argument("team", help="Team name, e.g. 'Manchester City'")
    positions.add_argument("--seasons", default="2023/2024")
    positions.add_argument("--league", default="ENG-Premier League")
    positions.add_argument("--cache-dir", default=None)
    positions.add_argument("--offline", action="store_true")

    matches = subparsers.add_parser("matches", help="Get head-to-head match results")
    matches.add_argument("team1")
    matches.add_argument("team2")
    matches.add_argument("--seasons", default="2023/2024")
    matches.add_argument("--league", default="ENG-Premier League")
    matches.add_argument("--cache-dir", default=None)
    matches.add_argument("--offline", action="store_true")

    predict = subparsers.add_parser("predict", help="Train models for a team pair")
    predict.add_argument("team1")
    predict.add_argument("team2")
    predict.add_argument("--seasons", default="2023/2024,2022/2023")
    predict.add_argument("--league", default="ENG-Premier League")
    predict.add_argument("--cache-dir", default=None)
    predict.add_argument("--offline", action="store_true")

    batch = subparsers.add_parser("batch-h2h", help="Analyze multiple team pairs")
    batch.add_argument("--pairs", required=True, help="Format: Team A|Team B;Team C|Team D")
    batch.add_argument("--seasons", default="2023/2024")
    batch.add_argument("--league", default="ENG-Premier League")
    batch.add_argument("--cache-dir", default=None)
    batch.add_argument("--offline", action="store_true")
    batch.add_argument("--export", default=None, help="Optional output .csv/.xlsx path")
    batch.add_argument("--plot", default=None, help="Optional output chart image path")

    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    parser = build_parser()
    args = parser.parse_args()
    seasons = parse_seasons(args.seasons)

    if args.command == "positions":
        df = get_team_position(args.team, leagues=args.league, seasons=seasons, cache_dir=args.cache_dir, offline=args.offline)
    elif args.command == "matches":
        df = get_match_results(args.team1, args.team2, leagues=args.league, seasons=seasons, cache_dir=args.cache_dir, offline=args.offline)
    elif args.command == "predict":
        df = get_match_results(args.team1, args.team2, leagues=args.league, seasons=seasons, cache_dir=args.cache_dir, offline=args.offline)
        metrics = predict_match_outcomes(df)
        logger.info("Model metrics: %s", metrics)
        return
    else:
        pairs = parse_pairs(args.pairs)
        df = batch_head_to_head(pairs, leagues=args.league, seasons=seasons, cache_dir=args.cache_dir, offline=args.offline)
        if args.export:
            export_path = export_results(df, args.export)
            logger.info("Exported data to %s", export_path)
        if args.plot and not df.empty:
            plot_path = plot_head_to_head_goals(df, args.plot)
            logger.info("Saved plot to %s", plot_path)

    if df.empty:
        logger.warning("No data found for the provided input.")
        return

    logger.info("Retrieved %s records.", len(df))
    logger.info("\n%s", df.to_string(index=False))


if __name__ == "__main__":
    main()
