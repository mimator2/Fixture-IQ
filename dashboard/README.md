# Fixture IQ — Player Workload & Performance Risk Dashboard

A data-driven React dashboard that visualises fixture congestion impact on Premier League footballers. Uses the **XGBoost Model B v4b** classifier to compute a single workload-associated risk score, rendered as four risk bands with SHAP explanations and workload timelines.

## Architecture

```
Master CSV (68K rows)
         ↓
feature_engineering_v4b.py    95 features (75 used by model), role assignment, goalkeeper exclusion
         ↓
prediction_v4b.py             XGBoost inference, minute guard, risk bands, reason generation
         ↓
export_data.py                Team aggregations, SHAP, player timelines, hypotheses
         ↓
public/data/*.json            Static JSON files
         ↓
React dashboard               TanStack Query hooks → components → pages
```

Everything runs **fully static** — no backend, no database, no environment variables. Data is pre-computed once by `export_data.py` and served as JSON.

## Quick Start

```bash
# 1. Generate data from CSV + XGBoost V4B (~2 min)
cd dashboard
python export_data.py

# 2. Install JS dependencies
npm install

# 3. Start dev server
npm run dev
```

The app runs at `http://localhost:5173`.

## Data Export

`python export_data.py` loads `Data/Fixture_IQ_Data_Seasons_2022-2025.csv`, runs the V4B XGBoost model, and writes files to `public/data/`:

| File | Description |
|------|-------------|
| `player_risks.json` | ~1,200 players with latest risk snapshot, risk band, monitoring flag, SHAP drivers, main risk reasons |
| `teams.json` | Premier League teams with aggregated metrics |
| `congestion_metrics.json` | Team-by-congestion-level breakdown |
| `hypotheses.json` | H1–H4 research hypotheses and evidence |
| `model_metadata.json` | Feature importances, risk bands, operating policy, feature group contributions |
| `player_timelines/{id}.json` | Per-player temporal slices for workload charts |

To refresh data after new matches are added to the CSV:

```bash
cd dashboard && python export_data.py
```

## V4B XGBoost Model

The dashboard uses **XGBoost V4B** as its single risk model:

| Property | Value |
|----------|-------|
| Algorithm | XGBClassifier (gradient-boosted trees) |
| Variant | `v4b_no_competition` — no raw competition one-hot encoding |
| Features | 75 (74 numeric + 1 categorical position) |
| Target | `fatigue_performance_risk` (performance underperformance ∨ load-reduction with fatigue context) |
| AUC-ROC | 0.634 |
| AUC-PR | 0.422 (1.38× over baseline) |
| Best threshold | 0.435 |

### Risk Bands

| Band | Range | Core Starter | Rotation Player |
|------|-------|-------------|-----------------|
| Low | 0 – 0.35 | Normal monitoring | Normal monitoring |
| Medium | 0.35 – 0.45 | Monitor response | Monitor response |
| High | 0.45 – 0.55 | Review minutes | Check wellness |
| Very High | 0.55 – 1.0 | Rest/recovery | Rest/recovery |

Alert thresholds: core_starter ≥ 0.45, rotation_player ≥ 0.50.

A positive flag does **not** mean the player must be rested. It means their workload, rest pattern, and injury context resemble situations historically associated with managed minutes or underperformance.

## Project Structure

```
dashboard/
├── public/data/          # Pre-computed JSON data files
│   ├── player_risks.json
│   ├── teams.json
│   ├── congestion_metrics.json
│   ├── hypotheses.json
│   ├── model_metadata.json
│   └── player_timelines/
├── src/
│   ├── components/       # Reusable UI components
│   │   ├── risk/         # Risk-specific (RiskBadge, ScoreGauge, FlagBadge, PlayerExplanation, etc.)
│   │   ├── ui/           # shadcn/ui primitives
│   │   ├── HeroSection.jsx, StatsOverview.jsx, HypothesisCards.jsx
│   │   ├── CongestionChart.jsx, RotationChart.jsx, TeamGrid.jsx
│   │   └── Layout.jsx    # Nav bar, mobile menu
│   ├── hooks/            # React Query hooks fetching from public/data/
│   │   ├── useTeams.js
│   │   ├── usePlayerRisks.js
│   │   ├── useCongestionMetrics.js
│   │   ├── useHypotheses.js
│   │   └── usePlayerTimeline.js
│   ├── pages/            # Route-level page components
│   │   ├── Home.jsx
│   │   ├── Team.jsx, TeamDetail.jsx
│   │   ├── PlayerMonitor.jsx, PlayerDetail.jsx
│   │   ├── ModelExplanation.jsx
│   │   ├── Hypothesis.jsx
│   │   └── DataSources.jsx
│   ├── lib/              # query-client.js, PageNotFound.jsx
│   ├── App.jsx           # Router (8 routes)
│   └── main.jsx          # Entrypoint
├── export_data.py        # Python: CSV → XGBoost V4B inference → JSON
├── package.json
├── vite.config.js
├── tailwind.config.js
├── eslint.config.js
└── README.md
```

## Pages

| Route | Purpose |
|-------|---------|
| `/` | Home dashboard: hero stats, congestion overview, risk distribution |
| `/teams` | Team list with risk and rotation summaries |
| `/team/:teamId` | Per-team detail: player table, workload breakdown |
| `/player-monitor` | Searchable/filterable player table with risk scores |
| `/player/:playerId` | Player drill-down: gauge, timeline, SHAP drivers, context panels |
| `/model-explanation` | Global model docs: importances, groups, thresholds, metrics |
| `/hypotheses` | H1–H4 evidence cards |
| `/data-sources` | Methodology and data provenance |

## Tech Stack

- **React 18** + **Vite 6** — build tooling
- **Tailwind CSS 3** — styling
- **shadcn/ui** — component primitives (Radix-based)
- **Recharts** — charts (bar, area, pie)
- **@tanstack/react-query** — data fetching & caching
- **lucide-react** — icons
- **Python 3.12** — data export
- **XGBoost** — V4B model inference
- **pandas / numpy / scikit-learn / shap** — feature engineering and explanations

## Related Projects

- `fatigue_monitor/` — Backend inference pipeline and original Streamlit dashboard
- `fatigue_monitor/src/prediction_v4b.py` — V4B XGBoost prediction pipeline
- `fatigue_monitor/src/feature_engineering_v4b.py` — V4B feature engineering
- `fatigue_monitor/models/xgboost_v4b/` — Trained model artifacts
- `models/CatBoostClassifier/` — CatBoost V6 complementary model
- `Data/Fixture_IQ_Data_Seasons_2022-2025.csv` — Source data

## Operational Notes

- The dashboard does **not** diagnose fatigue or prescribe selection decisions.
- Risk scores are computed on the most recent completed match per player.
- SHAP explanations are computed during export and stored in JSON for fast frontend rendering.
- A compatibility shim for XGBoost 3.x is applied during SHAP computation (`builtins.float` patch for bracketed `base_score` encoding).

## Usage Notes

- **No environment variables required** — the dashboard reads pre-computed JSON.
- **No database required** — all data is static files.
- To add new matches: update the master CSV in `Data/`, then re-run `python export_data.py`.
- Goalkeepers are excluded from model inference (risk score forced to 0).

## License

Internal research project — Fixture IQ Sports Analytics.
