# TEMFPA – Football Prediction & Analysis

This project is a football prediction and analysis tool built with Python. It uses the [soccerdata](https://pypi.org/project/soccerdata/) library to retrieve historical league tables and match results, and then organizes that data into clean pandas DataFrames for further analysis.

## Features

- **Reusable Python package** – notebook retrieval logic is now available as importable modules.
- **Historical team positions** – fetch league table placements for a team across multiple seasons.
- **Match results analysis** – retrieve head‑to‑head matches, infer winners, and return a DataFrame.
- **Machine learning predictions** – train logistic regression and random forest models on historical fixtures.
- **Extended metrics** – derive goals scored, total goals, goal difference, and expected-goals proxy (`home_xg`/`away_xg`).
- **Data visualization** – generate goals charts for fixtures.
- **Batch head-to-head analysis** – process multiple team-pair analyses at once and export to CSV/Excel.
- **Command-line interface** – run analysis from the terminal without opening Jupyter.
- **Local caching for persistence** – fetched FotMob league tables and schedules are cached for faster repeat queries and offline analysis.

## Project Structure

```text
TEMFPA/
├── notebook.ipynb
├── pyproject.toml
├── setup.py
├── src/
│   └── temfpa/
│       ├── __init__.py
│       ├── cli.py
│       └── retrieval.py
└── tests/
    └── test_retrieval.py
```

## Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

The pinned versions in `requirements.txt` make the notebook and package dependencies reproducible across environments.

## Python API

```python
from temfpa import get_team_position, get_match_results

positions = get_team_position(
    "Manchester City",
    seasons=["2023/2024", "2022/2023"],
)

results = get_match_results(
    "Manchester City",
    "Liverpool",
    seasons=["2023/2024", "2022/2023"],
)
```

## CLI Usage

Team league positions:

```bash
temfpa positions "Manchester City" --seasons "2023/2024,2022/2023"
```

Head-to-head match results:

```bash
temfpa matches "Manchester City" "Liverpool" --seasons "2023/2024,2022/2023"
```

Optional flags:
- `--league` (default: `ENG-Premier League`)
- `--cache-dir` (default: `$TEMFPA_CACHE_DIR` or `~/.cache/temfpa`)
- `--offline` (use cached data only, no network calls)

You can also set `TEMFPA_CACHE_DIR` to configure a persistent cache location for scripts and notebooks.

## Testing

```bash
pytest -q
```


## Extended CLI

```bash
# model benchmarking
temfpa predict "Manchester City" "Liverpool" --seasons "2023/2024,2022/2023"

# batch H2H + export + chart
temfpa batch-h2h --pairs "Manchester City|Liverpool;Real Madrid|Barcelona" --seasons "2023/2024" --export reports/h2h.xlsx --plot reports/goals.png
```
