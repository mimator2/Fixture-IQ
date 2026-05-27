# FixtureIQ Repository Restructuring Plan

> **Status**: Planned — not yet executed
> **Date**: 2026-05-22

---

## Goals

1. **Modularization** — Break monolithic scripts into focused, reusable modules.
2. **Clear naming** — Every file says what it does on the tin.
3. **Correct path resolution** — No more `../../Data/Dynamic_2425/` hardcodes; one centralized `paths.py` module.
4. **Standardized data layout** — Organise data by season first, source second.
5. **Secrets hygiene** — API tokens in `.env` (gitignored), not committed.

---

## 1. Proposed Directory Layout

```
Fixture-IQ-playground/
│
├── .env                          # Secrets (gitignored)
├── .env.example                  # Template without real values
├── .gitignore                    # Updated: data/, .env, notebooks/ added
├── README.md                     # One project overview (replace FBref-only doc)
├── PLAN.md                       # This file
├── requirements.txt              # Complete dependency list
│
├── src/                          # Reusable Python modules
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── paths.py              # Central path resolution (all scripts import this)
│   ├── data/
│   │   ├── __init__.py
│   │   ├── fbref_pipeline.py     # FBref scraping (from Data_Extraction/football_data_pipeline.py)
│   │   ├── sofascore_pipeline.py # SofaScore player pipeline (from Data_Extraction/sofascore_pipeline.py)
│   │   ├── dynamic_pipeline.py   # Dynamic congestion pipeline (from Data_Extraction/fixtureiq_dynamic_elite.py)
│   │   ├── raw_downloader.py     # Raw PL-centric downloader (from Data_Extraction/raw_elite_downloader.py)
│   │   └── context_extractor.py  # ClubElo + Understat (from Data_Extraction/extract_context.py)
│   ├── features/
│   │   ├── __init__.py
│   │   ├── engineering.py        # ACWR, rolling windows, congestion flags, etc.
│   │   └── target.py             # Target variable definition (fatigue_risk proxy)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── train.py              # Training: CV, hyperparameter search
│   │   ├── predict.py            # Inference: single player, batch, manual
│   │   └── evaluate.py           # Metrics, SHAP analysis, plots
│   └── visualization/
│       ├── __init__.py
│       └── dashboard.py          # Streamlit app (from scripts/app.py)
│
├── scripts/                      # Thin CLI entry points
│   ├── extract_fbref.py          # Consolidates 4 run_season_*.py scripts
│   ├── extract_sofascore.py      # CLI wrapper for SofaScore pipeline
│   ├── extract_dynamic.py        # CLI wrapper for dynamic pipeline
│   ├── extract_context.py        # CLI wrapper for context extractor
│   ├── train_model.py            # CLI wrapper for training
│   ├── predict.py                # CLI wrapper for inference
│   └── test_predictions.py       # Keeep, update imports
│
├── notebooks/                    # Renamed from EDA/
│   ├── 01_data_preparation/
│   ├── 02_exploration/
│   ├── 03_modeling/
│   └── LOGOS/
│
├── data/                         # Data restructured by season
│   ├── 2020-2021/
│   │   ├── sofascore/
│   │   │   ├── premier_league/
│   │   │   └── champions_league/
│   │   └── fbref/
│   ├── 2021-2022/
│   │   ├── sofascore/champions_league/
│   │   └── fbref/
│   ├── 2022-2023/
│   │   ├── fbref/
│   │   ├── sofascore_dynamic/       # Dynamic pipeline output
│   │   ├── sofascore_raw_pl_centric/
│   │   └── injuries/
│   ├── 2023-2024/
│   │   ├── fbref/
│   │   ├── sofascore_dynamic/
│   │   ├── sofascore_raw_pl_centric/
│   │   └── injuries/
│   ├── 2024-2025/
│   │   ├── fbref/
│   │   ├── sofascore/premier_league/
│   │   ├── sofascore/champions_league/
│   │   ├── sofascore_dynamic/
│   │   ├── sofascore_raw_pl_centric/
│   │   └── injuries/
│   ├── clubelo_understat/           # Season-independent
│   └── cache/                       # SofaScore per-match cache (from .fixtureiq_cache/)
│
├── docs/
│   ├── data_dictionary.md
│   ├── plan_fatigue_model.md
│   └── architecture.md              # From Data_Extraction/Fixture_Dynamic.md
│
├── models/                          # Trained artifacts (keep as-is)
├── results/
│   └── figures/                     # Subdirectory for PNGs
│
└── (cleanup)
    - Data_Extraction/README.md      → delete (duplicate)
    - Data/Data.md                   → delete (duplicate of docs/data_dictionary.md)
    - TFP.odt                        → move to docs/ or archive
```

---

## 2. Data Migration Map

### 2.1 FBref data (currently `Data/SEASON_YYYY_YYYY/`)

| Current | Future |
|---------|--------|
| `Data/SEASON_2022_2023/{team}/` | `data/2022-2023/fbref/{team}/` |
| `Data/SEASON_2023_2024/{team}/` | `data/2023-2024/fbref/{team}/` |
| `Data/SEASON_2024_2025/{team}/` | `data/2024-2025/fbref/{team}/` |

### 2.2 SofaScore data (currently `Data/Premier_League/` + `Data/Champions_League/`)

| Current | Future |
|---------|--------|
| `Data/Premier_League/2020_2021/` | `data/2020-2021/sofascore/premier_league/` |
| `Data/Champions_League/2020_2021/` | `data/2020-2021/sofascore/champions_league/` |
| ... same pattern for 2021-2022 through 2024-2025 | |

### 2.3 Dynamic pipeline output (currently `Data/Data_Dynamic_*/`)

| Current | Future |
|---------|--------|
| `Data/Data_Dynamic_2223/` | `data/2022-2023/sofascore_dynamic/` |
| `Data/Data_Dynamic_2324/` | `data/2023-2024/sofascore_dynamic/` |
| `Data/Data_Dynamic_2425/` | `data/2024-2025/sofascore_dynamic/` |

### 2.4 Raw PL-centric data

| Current | Future |
|---------|--------|
| `Data/Data_Raw_PL_Centric/` | `data/2023-2024/sofascore_raw_pl_centric/` (plus 24-25) |

### 2.5 Injuries (currently `Data/Injuries/`)

| Current | Future |
|---------|--------|
| `Data/Injuries/SEASON_2022-2023/` | `data/2022-2023/injuries/` |
| `Data/Injuries/SEASON_2023-2024/` | `data/2023-2024/injuries/` |
| `Data/Injuries/SEASON_2024-2025/` | `data/2024-2025/injuries/` |

### 2.6 Season-independent data

| Current | Future |
|---------|--------|
| `Data/Clubelo_Understat/` | `data/clubelo_understat/` |
| `.fixtureiq_cache/` | `data/cache/` |

---

## 3. Module Breakdown

### 3.1 `src/config/paths.py` — Central Path Resolution

```python
from pathlib import Path

def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent

def data_dir() -> Path:
    return project_root() / 'data'

def season_dir(season: str) -> Path:
    return data_dir() / season

def model_dir() -> Path:
    return project_root() / 'models'

def results_dir() -> Path:
    return project_root() / 'results'

def cache_dir() -> Path:
    return data_dir() / 'cache'

def get_dynamic_path(season: str) -> Path:
    return season_dir(season) / 'sofascore_dynamic'

def get_fbref_path(season: str, team: str = None) -> Path:
    base = season_dir(season) / 'fbref'
    return base / team if team else base
```

Every script imports these functions instead of hardcoding relative paths.

### 3.2 `scripts/extract_fbref.py` — Consolidated Entry Point

Replaces 4 `run_season_*.py` files:

```python
# Usage:
#   python scripts/extract_fbref.py --season 2024-2025 --teams arsenal,liverpool,man_city,aston_villa
#   python scripts/extract_fbref.py --season 2024-2025 --all-pl-teams
#   python scripts/extract_fbref.py --season 2022-2023 --teams man_city,liverpool --headless
```

Uses `argparse` with the following flags:
- `--season` (required or defaults to latest)
- `--teams` (comma-separated list)
- `--all-pl-teams` (auto-discover all 20 PL teams)
- `--headless` (run Selenium in headless mode)

### 3.3 `src/features/engineering.py` — Feature Engineering

Extracted from `scripts/train_fatigue_model.py` (~lines 100-250):

Functions (each independently testable):
- `compute_rest_days(match_dates)` — days since last match
- `compute_acwr(minutes_7d, minutes_28d)` — acute:chronic workload ratio
- `compute_rolling_stats(df, window, cols)` — rolling averages/std for ratings
- `flag_congestion(rest_days, threshold=3)` — high congestion boolean
- `lineup_churn(starting_xi_current, starting_xi_prev)` — squad rotation measure
- `build_engineered_features(raw_df)` — orchestrator calling all of the above

### 3.4 `src/features/target.py` — Target Variable

Defines the composite `fatigue_risk` proxy:

```python
def compute_fatigue_risk(df) -> pd.Series:
    """
    fatigue_risk = 1 if >= 2 of 3 signals are true:
      1. ACWR in danger zone (< 0.5 or > 1.5)
      2. Performance decline (rating > 1.0 below 5-match rolling avg)
      3. High congestion (rest <= 3 days)
    """
```

### 3.5 `src/models/train.py` — Training Pipeline

Extracted from `scripts/train_fatigue_model.py` (~lines 300-600):

- `load_training_data(seasons: list)` — loads from data dir
- `setup_pipeline(X, y)` — preprocessor (scaler, encoder)
- `train_xgboost(X_train, y_train, params)` — train with given params
- `time_series_cv(X, y, n_splits=5)` — cross-validation preserving time order
- `hyperparameter_search(X, y, param_grid)` — grid/random search
- `save_artifacts(model, preprocessor, feature_cols, threshold)` — persist to models/

### 3.6 `src/models/evaluate.py` — Evaluation & Interpretation

Extracted from `scripts/train_fatigue_model.py` (~lines 601-787):

- `classification_report(y_true, y_pred, threshold)` — precision, recall, F1, ROC-AUC, PR-AUC
- `plot_roc_pr_curves(y_true, y_proba, save_path)` — saves to results/figures/
- `shap_analysis(model, X, save_path)` — SHAP summary + bar plots
- `feature_importance_plot(model, feature_names, save_path)` — XGBoost native importance
- `ucl_comparison_plot(df, save_path)` — UCL vs non-UCL fatigue risk comparison

### 3.7 `src/models/predict.py` — Inference

Refactored from `scripts/predict_fatigue.py`:

- `FatiguePredictor` class:
  - `__init__(model_path, preprocessor_path, feature_columns_path, threshold_path)`
  - `predict_player(player_name, season, match_data)` — lookup and predict
  - `predict_manual(features_dict)` — raw feature input
  - `predict_batch(csv_path)` — batch CSV prediction

### 3.8 `src/visualization/dashboard.py` — Streamlit Dashboard

Moved from `scripts/app.py` and refactored to import from `src.features`, `src.models`, `src.config` instead of duplicating logic.

---

## 4. Environment & Configuration

### 4.1 `.env` file (gitignored)

```
SCRAPE_DO_TOKEN=<your_token_here>
# Future: API-Football key, etc.
```

### 4.2 `.env.example` (tracked)

```
SCRAPE_DO_TOKEN=your_token_here
```

### 4.3 Updated `.gitignore`

```
# Environments
.venv/
.env

# Data (regenerated by pipelines)
data/

# Notebooks (large, regenerable)
notebooks/

# OS
.DS_Store
Thumbs.db

# Python
__pycache__/
*.pyc
*.pyo
```

**Keep tracked**: `models/`, `results/`, `src/`, `scripts/`, `docs/`, `requirements.txt`

---

## 5. Dependencies to Add to `requirements.txt`

Currently missing from `requirements.txt` but used by the codebase:

```
xgboost
scikit-learn
streamlit>=1.28
seaborn
shap
plotly
ScraperFC
soccerdata
python-dotenv>=1.0
undetected-chromedriver
cloudscraper
playwright
```

---

## 6. Cleanup — Duplicates to Delete

| File | Reason |
|------|--------|
| `Data_Extraction/README.md` | Duplicate of root `README.md` (FBref doc) |
| `Data/Data.md` | Duplicate of `docs/data_dictionary.md` |
| `TFP.odt` (at root) | Should move to `docs/` or archive |

---

## 7. Execution Order

1. **Write new `src/` modules** — create `paths.py`, then move/refactor extraction scripts
2. **Write `scripts/` entry points** — thin wrappers with CLI args
3. **Update `requirements.txt`** — add all missing dependencies
4. **Move data directories** — into the new season-first layout
5. **Update `.gitignore` and create `.env`/`.env.example`**
6. **Write/update `README.md`** — one coherent project overview
7. **Clean up duplicates** — delete `Data_Extraction/README.md`, `Data/Data.md`, move `TFP.odt`
8. **Move `EDA/` → `notebooks/`**
9. **Verify** — run `extract_fbref.py --help`, `train_model.py`, `predict.py` to confirm imports resolve

---

## Appendix: Key Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **Scripts + `sys.path` (not pip package)** | User prefers simple scripts; avoids `pip install -e .` overhead |
| **Season-first data layout** | Primary analysis axis is season; all queries filter by it |
| **Thin CLI entry points** | CLI scripts stay small; all logic lives in `src/` (testable) |
| **`src/config/paths.py` for path resolution** | Eliminates fragile relative-path hardcoding across every script |
| **Feature engineering in `src/features/`** | Shared between training pipeline and dashboard (no duplication) |
