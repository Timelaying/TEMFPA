# TEMFPA – Football Prediction & Analysis

This project is a football prediction and analysis tool built with Python. It uses the [soccerdata](https://pypi.org/project/soccerdata/) library to retrieve historical league tables and match results, and then organizes that data into clean pandas DataFrames for further analysis.

## Features

- **Reusable Python package** – notebook retrieval logic is now available as importable modules.
- **Historical team positions** – fetch league table placements for a team across multiple seasons.
- **Match results analysis** – retrieve head‑to‑head matches, infer winners, and return a DataFrame.
- **Command-line interface** – run analysis from the terminal without opening Jupyter.

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
pip install -e .
```

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

## Testing

```bash
pytest -q
```
