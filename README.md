# TEMFPA – Football Prediction & Analysis

TEMFPA is a Python toolkit for football data retrieval, head-to-head analysis, and simple match-outcome modeling. It builds on [`soccerdata`](https://pypi.org/project/soccerdata/) and returns clean `pandas` DataFrames for scripting, notebooks, and CLI workflows.

## Features

- Reusable package API for league table and fixture retrieval.
- Head-to-head match extraction with winner inference (`home`, `away`, or `Draw`).
- Derived metrics including goal difference, total goals, and rolling xG proxies.
- Baseline model benchmarking with logistic regression and random forest classifiers.
- Batch processing for multiple team pairs.
- CSV/XLSX export utilities and goals chart generation.
- File-based local caching with optional offline mode.
- Command-line interface for all major workflows.

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## Quick Start (Python API)

```python
from temfpa import get_match_results, get_team_position
from temfpa.analytics import add_match_metrics, predict_match_outcomes

positions = get_team_position(
    "Manchester City",
    seasons=["2023/2024", "2022/2023"],
)

matches = get_match_results(
    "Manchester City",
    "Liverpool",
    seasons=["2023/2024", "2022/2023"],
)

metrics = add_match_metrics(matches)
benchmark = predict_match_outcomes(matches)
```

## CLI Usage

Get league positions for one team:

```bash
temfpa positions "Manchester City" --seasons "2023/2024,2022/2023"
```

Get head-to-head match results:

```bash
temfpa matches "Manchester City" "Liverpool" --seasons "2023/2024,2022/2023"
```

Run prediction benchmark:

```bash
temfpa predict "Manchester City" "Liverpool" --seasons "2023/2024,2022/2023"
```

Batch analyze multiple pairs and export:

```bash
temfpa batch-h2h \
  --pairs "Manchester City|Liverpool;Real Madrid|Barcelona" \
  --seasons "2023/2024" \
  --export reports/h2h.xlsx \
  --plot reports/goals.png
```

Optional flags shared across commands:

- `--league` (default: `ENG-Premier League`)
- `--cache-dir` (default: `$TEMFPA_CACHE_DIR` or `~/.cache/temfpa`)
- `--offline` (uses cache only; no network calls)

## Cache Behavior

TEMFPA caches league tables and schedules per `(category, league, season)` tuple in pickle files.

- By default, cache files are written to `~/.cache/temfpa`.
- Set `TEMFPA_CACHE_DIR` to use another persistent location.
- Use `--offline` (CLI) or `offline=True` (API) to force cache-only behavior.

## Development

Run tests:

```bash
pytest -q
```

## Project Structure

```text
TEMFPA/
├── README.md
├── pyproject.toml
├── requirements.txt
├── setup.py
├── src/
│   └── temfpa/
│       ├── __init__.py
│       ├── analytics.py
│       ├── cli.py
│       └── retrieval.py
└── tests/
    ├── test_analytics.py
    └── test_retrieval.py
```
