# Fixture IQ — Player Workload & Performance Risk Dashboard

A data-driven React dashboard that visualises fixture congestion impact on Premier League footballers. Uses **CatBoost V6 ML models** to compute dual risk scores — a pure workload/fatigue signal (No Rating Baseline) and a performance-risk score (Full model with rating baseline).

## Architecture

```
CSV (68K rows) → export_data.py → V6 models → public/data/*.json → React hooks → components
```

Everything runs **fully static** — no backend, no database, no environment variables. Data is pre-computed once and served as JSON.

## Quick Start

```bash
# 1. Generate data from CSV + ML models (~2 min)
cd dashboard
python export_data.py

# 2. Install JS dependencies
npm install

# 3. Start dev server
npm run dev
```

The app runs at `http://localhost:5173`.

## Data Export

`python export_data.py` loads `XgBoost_model/Fixture_IQ_Data_Seasons_2022-2025.csv`, runs both V6 CatBoost models, and writes four files to `public/data/`:

| File | Rows | Description |
|------|------|-------------|
| `player_risks.json` | ~1,200 | Per-player latest risk snapshot with fatigue score, performance risk, flags, minutes load, injury context |
| `teams.json` | 20 | Premier League team aggregates (matches, avg rest, pts/match, season) |
| `congestion_metrics.json` | ~30 | Team-by-congestion-level breakdown (Low/Medium/High rest) |
| `hypotheses.json` | 4 | Research hypotheses and current evidence status |

To refresh data after new matches are added to the CSV:

```bash
cd dashboard && python export_data.py
```

No other steps needed — the React app reads directly from the generated JSON files.

## Dual-Score System (V6 CatBoost)

The dashboard uses two CatBoost classifiers trained on engineered features (rolling windows, position-adjusted z-scores, competition transitions, injury context):

| Score | Model | What it measures | Used by |
|-------|-------|------------------|---------|
| Fatigue Score | V6 No Rating Baseline | Pure workload signal: minutes, rest, competition density, action load | Coaches / medical staff |
| Performance Risk | V6 Full | Fatigue + recent rating baseline (avg rating last 3/5 matches) | Analysts |

Both output a **0–1 probability** mapped to four risk bands:

| Band | Range | Core Starter Action | Rotation Player Action |
|------|-------|-------------------|----------------------|
| Low | 0 – 0.25 | Normal Monitoring | Normal Monitoring |
| Medium | 0.25 – 0.45 | Monitor Training Response | Monitor Training Response |
| High | 0.45 – 0.65 | Review Minutes Plan | Check GPS/Wellness/Soreness |
| Very High | > 0.65 | Consider Rest / Recovery Protocol | Consider Rest / Recovery Protocol |

## Project Structure

```
dashboard/
├── public/data/          # Pre-computed JSON data files
│   ├── player_risks.json
│   ├── teams.json
│   ├── congestion_metrics.json
│   └── hypotheses.json
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── risk/         # Risk-specific (RiskBadge, ScoreGauge, FlagBadge, etc.)
│   │   └── ui/           # shadcn/ui primitives
│   ├── hooks/            # React Query hooks fetching from public/data/
│   │   ├── useTeams.js
│   │   ├── usePlayerRisks.js
│   │   ├── useCongestionMetrics.js
│   │   ├── useHypotheses.js
│   │   └── usePlayerTimeline.js
│   ├── pages/            # Route-level page components
│   ├── App.jsx           # Router setup
│   └── index.css         # Tailwind + custom styles
├── export_data.py        # Python script: CSV → ML → JSON
├── package.json
├── vite.config.js
└── README.md
```

## Tech Stack

- **React 18** + **Vite** — build tooling
- **Tailwind CSS 3** — styling
- **shadcn/ui** — component primitives (Radix-based)
- **Recharts** — charts (bar, radar, pie, area)
- **@tanstack/react-query** — data fetching & caching
- **lucide-react** — icons
- **Python 3.12** — data export
- **CatBoost** — V6 ML models
- **pandas / numpy** — feature engineering

## Related Projects

- `fatigue_monitor/` — Original Streamlit multipage app (kept for reference)
- `fatigue_monitor/src/prediction_v6.py` — V6 CatBoost prediction pipeline
- `fatigue_monitor/src/feature_engineering_v6.py` — V6 feature engineering
- `fatigue_monitor/models/catboost_v6/` — Trained model artifacts
- `XgBoost_model/Fixture_IQ_Data_Seasons_2022-2025.csv` — Source data

## License

Internal research project — Fixture IQ Sports Analytics.
