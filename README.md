# TEMFPA – Football Prediction & Analysis

TEMFPA is a Python toolkit for football data retrieval, head-to-head analysis, and simple match-outcome modeling. It builds on [`soccerdata`](https://pypi.org/project/soccerdata/) and returns clean `pandas` DataFrames for scripting, notebooks, and CLI workflows.

## Features

- Reusable package API for league table and fixture retrieval.
- Head-to-head match extraction with winner inference (`home`, `away`, or `Draw`).
- Derived metrics including goal difference, total goals, and rolling xG proxies.
- Baseline model benchmarking with logistic regression and random forest classifiers.
- Batch processing for multiple team pairs.
- CSV/XLSX export utilities and goals chart generation.
- Frontend football analytics dashboard with Chart.js visualisations for league position, goals scored vs conceded, W/D/L mix, head-to-head outcomes, prediction probabilities, and recent form timelines.
- File-based or SQLite-backed local caching with optional offline mode.
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
- `--db-path` (optional SQLite cache path; overrides file cache when set)
- `--offline` (uses cache only; no network calls)

## Cache Behavior

TEMFPA caches league tables and schedules per `(category, league, season)` tuple. By default it stores pickle files, and it can also store cached frames in a SQLite database.

- By default, cache files are written to `~/.cache/temfpa`.
- Set `TEMFPA_CACHE_DIR` to use another persistent file-cache location.
- Pass `--db-path data/temfpa.sqlite`, set `TEMFPA_DB_PATH`, or pass `db_path=` in Python to use SQLite instead of the file cache.
- Use `--offline` (CLI) or `offline=True` (API) to force cache-only behavior.

Example SQLite-backed CLI usage:

```bash
temfpa matches "Manchester City" "Liverpool" \
  --seasons "2023/2024,2022/2023" \
  --db-path data/temfpa.sqlite
```

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

## Frontend

A responsive product landing page is available in [`frontend/`](frontend/). It is built with
plain HTML, CSS, and JavaScript, so it does not require a separate package installation or
build step.

Run it locally from the repository root:

```bash
python -m http.server 8000 --directory frontend
```

Then open `http://localhost:8000` in a browser.
