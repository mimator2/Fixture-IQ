# FixtureIQ — Football Fatigue & Congestion Analysis

Multi-source data pipeline and ML model for analyzing fixture congestion's impact on player performance and injury risk in Premier League and Champions League football.

## Project Structure

```
├── src/                    # Reusable Python modules
│   ├── config/paths.py     # Centralized path resolution
│   ├── data/               # Data extraction pipelines
│   │   ├── fbref_pipeline.py      # FBref scraping (Selenium + cloudscraper)
│   │   ├── sofascore_pipeline.py   # SofaScore via ScraperFC
│   │   ├── dynamic_pipeline.py     # Dynamic congestion pipeline
│   │   ├── raw_downloader.py       # PL-centric raw downloader
│   │   └── context_extractor.py    # ClubElo + Understat
│   ├── features/           # Feature engineering & target definition
│   │   ├── engineering.py  # ACWR, rolling windows, congestion flags
│   │   └── target.py       # Composite fatigue_risk proxy
│   ├── models/             # XGBoost training, evaluation, inference
│   │   ├── train.py
│   │   ├── evaluate.py
│   │   └── predict.py
│   └── visualization/
│       └── dashboard.py    # Streamlit dashboard
├── scripts/                # CLI entry points
│   ├── extract_fbref.py
│   ├── extract_sofascore.py
│   ├── extract_dynamic.py
│   ├── extract_context.py
│   ├── train_model.py
│   ├── predict.py
│   └── test_predictions.py
├── notebooks/              # Jupyter notebooks
│   ├── 01_data_preparation/
│   ├── 02_exploration/
│   ├── 03_modeling/
│   └── LOGOS/
├── data/                   # Data by season then source (gitignored)
│   ├── YYYY-YYYY/
│   │   ├── fbref/
│   │   ├── sofascore/premier_league/
│   │   ├── sofascore/champions_league/
│   │   ├── sofascore_dynamic/
│   │   ├── sofascore_raw_pl_centric/
│   │   └── injuries/
│   ├── clubelo_understat/
│   └── cache/
├── models/                 # Trained model artifacts
├── results/                # Evaluation outputs (figures, reports)
└── docs/                   # Documentation
```

## Data Sources

| Source | Scope | Method |
|--------|-------|--------|
| **FBref** | Match logs, player stats, rosters, match reports (PL + UCL teams, 2022-2025) | Selenium + cloudscraper + scrape.do |
| **SofaScore** | Per-player match ratings, heatmaps, position profiles (all PL + UCL, 2020-2025) | ScraperFC |
| **ClubElo** | Team strength ratings (historical) | `soccerdata` library |
| **Understat** | xG, key passes, shot data (PL) | `soccerdata` library |

## Target: Fatigue Risk Proxy

Composite binary target defined as `fatigue_risk = 1` when >= 2 of 3 signals are true:
1. **ACWR danger zone** (< 0.5 or > 1.5)
2. **Performance decline** (rating > 1.0 below 5-match rolling avg)
3. **High congestion** (rest <= 3 days)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Download context data (ClubElo + Understat)
python scripts/extract_context.py

# Train fatigue risk model
python scripts/train_model.py

# Predict a player's fatigue risk
python scripts/predict.py --player "Bukayo Saka" --team "Arsenal"

# Launch dashboard
streamlit run src/visualization/dashboard.py
```

## CLI Reference

| Command | Purpose |
|---------|---------|
| `scripts/extract_fbref.py` | Extract FBref data for PL/UCL teams |
| `scripts/extract_sofascore.py` | Extract SofaScore player data |
| `scripts/extract_dynamic.py` | Run dynamic congestion pipeline |
| `scripts/extract_context.py` | Fetch ClubElo + Understat data |
| `scripts/train_model.py` | Train XGBoost fatigue risk model |
| `scripts/predict.py` | Predict player fatigue risk |
| `scripts/test_predictions.py` | Batch prediction tests |

## Seasons Covered

- **2020-2021** through **2024-2025**: SofaScore PL + UCL
- **2022-2023** through **2024-2025**: FBref (UCL-participant PL teams)
