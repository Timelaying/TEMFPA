# TEMFPA – Football Prediction & Analysis

This project is a football prediction and analysis tool built with Python and Jupyter notebooks. It uses the [soccerdata](https://pypi.org/project/soccerdata/) library to retrieve historical league tables and match results, and then organizes that data into clean pandas DataFrames for further analysis. The notebook can be used to explore how teams have performed across multiple seasons, compare head‑to‑head results between two clubs, and lay the groundwork for more advanced predictive modelling.

## Features

- **Historical team positions** – fetches league tables for a given team across multiple seasons and collates their finishing positions.
- **Match results analysis** – retrieves the match schedule for two teams, converts scores to integers, determines winners and draws, and builds a results DataFrame.
- **Head‑to‑head comparison** – compares historical performance between two clubs over several seasons.
- **Data summarization** – outputs pandas DataFrames that you can inspect, visualize or feed into machine learning models.

## Tech Stack

- **Python** – core programming language.
- **Jupyter Notebook** – interactive development environment (`notebook.ipynb`).
- **pandas** – data manipulation and analysis.
- **soccerdata** – library for accessing football data from sources like FotMob.
- *Optional:* **NumPy**, **Matplotlib** – for numerical analysis and plotting if you extend the notebook.

## Project Structure

```
TEMFPA/
├── notebook.ipynb        # Jupyter notebook with data collection and analysis functions
├── READ.me              # Legacy read me (not used)
└── README.md            # You are here
```

## Getting Started

1. **Clone the repository**

```bash
git clone https://github.com/Timelaying/TEMFPA.git
cd TEMFPA
```

2. **Install dependencies**  
   Create a virtual environment (recommended) and install the required libraries:

```bash
python -m venv venv
source venv/bin/activate     # On Windows use: venv\Scripts\activate
pip install soccerdata pandas jupyter
```

3. **Run the notebook**

```bash
jupyter notebook notebook.ipynb
```

   Modify the `team_name`, `team1`, and `team2` variables in the notebook to select the teams you’re interested in, and adjust the `seasons` list to define the seasons you want to analyse. Then run the cells to fetch and view the data.

## Roadmap

- Add machine learning models (e.g. logistic regression, random forest) to predict match outcomes based on historical data.
- Incorporate additional leagues, competitions, and metrics (e.g. goals scored, goal difference, expected goals).
- Add data visualization (plots and charts) to make insights easier to digest.
- Package the data collection functions into a reusable Python module.

## License

This project is open‑source and available under the MIT License. See the [LICENSE](LICENSE) file for details.
