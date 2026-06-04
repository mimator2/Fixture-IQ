# Fatigue Monitor Dashboard — Model B v4b

Streamlit dashboard for post-match workload-associated risk monitoring. Predicts which players may be at elevated risk of reduced performance or managed minutes in the next fixture, based on rolling workload, multi-competition burden, and physical effort features.

## Architecture

```
fatigue_monitor/
├── app.py                          # Entry point — sidebar, nav, dark theme
├── views/
│   ├── team_overview.py            # Latest match per player: KPIs, charts, table
│   ├── player_detail.py            # Per-player drill-down with 5 context sections
│   └── model_explain.py            # Feature importance, per-player drivers, policy
├── src/
│   ├── config.py                   # Paths, operating policy, risk bands, colors
│   ├── feature_engineering.py      # v4 feature pipeline (rolling, burden, v4)
│   └── prediction.py               # load_artifacts(), predict_fatigue_risk(), explanations
└── models/model_b_v4b/             # Saved artifacts (5 .pkl + metadata.json)
    ├── xgb_model.pkl               # Trained XGBClassifier
    ├── preprocessor.pkl            # ColumnTransformer (num median + cat OHE)
    ├── num_features.pkl            # 77 numerical feature names
    ├── cat_features.pkl            # ["player_position"]
    ├── policy.pkl                  # Operating policy dict
    └── metadata.json               # Training date, metrics, feature counts
```

Each page uses the latest match per player (deduplicated by `player_name`, taking the most recent `date`).

## Pages

### Team Overview
- **KPI cards**: unique players, flagged %, avg risk score, High/Very High counts
- **Risk band distribution** bar chart (Plotly)
- **Role breakdown** grouped bar (Total vs Flagged)
- **Filters**: team, position, role, risk band, monitoring flag
- **Sortable player table**: top 50 by risk score with risk badges, flag labels, driver explanations
- **Player selector** with "View Player Detail" button

### Player Detail
- **A. Current Risk**: gauge chart (animated), risk score/band/flag/role/threshold
- **Main Risk Drivers**: explanation bullets from rule-based feature analysis
- **B. Workload Context**: minutes last 14d/21d, starts, full 90s, rest days, short-rest matches
- **C. Multi-Competition Context**: UCL minutes, cup minutes, PL-after-UCL flags, comp switches
- **D. Physical Effort**: duels, tackles, fouls, dribbles (14d), Physical Load Index
- **E. Squad Context**: injured count, soft tissue, returning-from-injury, fixtures missed
- **Squad Comparison**: scatter plot (minutes vs risk, sized by full 90s, colored by role)

### Model Explanation
- **Top-20 Feature Importance**: horizontal bar (XGBoost gain), color-coded by importance quartile
- **Feature Category Breakdown**: grouped importance (Workload Volume, Rest & Recovery, UCL, Cup, Transitions, Physical Effort, Position, Squad, Player-Relative)
- **Per-Player Feature Drivers**: top 10 features with direction (↑/↓) for a selected player
- **Threshold Policy**: core_starter ≥ 0.45, rotation_player ≥ 0.50
- **Risk Bands table**: Low / Medium / High / Very High ranges
- **Model Limitations** expander

## Usage

```bash
# Install dependencies
pip install streamlit pandas numpy scikit-learn xgboost joblib plotly

# Launch dashboard
streamlit run fatigue_monitor/app.py
```

From the sidebar:
1. **Master CSV** — click "Load Master Data & Predict" to run inference on the full dataset
2. **Upload CSV** — upload a custom player-match CSV with the same schema
3. **Export Results CSV** — download prediction results after loading

## Data Source

Master CSV: `XgBoost_model/Fixture_IQ_Data_Seasons_2022-2025.csv`

Required columns: `date`, `player_name`, `player_team`, `player_position`, `minutes_played`, `rating`, `rest_days`, and all features consumed by the engineering pipeline.

## Model

| Metric | Value |
|---|---|
| Test AUC-ROC | 0.627 |
| Test AUC-PR | 0.390 |
| Base rate | 0.286 |
| Best threshold | 0.449 |
| Numerical features | 77 |
| Categorical features | 1 (`player_position`) |

### Training

```bash
python train_v4.py
```

Reproduces the full v4 pipeline:
1. Load CSV → engineer features → Stage 1 regressor (context-only) → performance residuals
2. Role assignment → target construction (underperformance ∨ load reduction)
3. Train XGBClassifier with temporal split (2022 train, 2023 val, 2024 test)
4. Save 5 artifacts + metadata.json

### Risk Interpretation

| Score | Band | Monitoring |
|---|---|---|
| < 0.25 | Low | Clear |
| 0.25 – 0.45 | Medium | Clear |
| 0.45 – 0.65 | High | Monitor (core_starter) / Clear (rotation_player) |
| > 0.65 | Very High | Monitor |

- **core_starter threshold**: 0.45
- **rotation_player threshold**: 0.50

## Limitations

- Not a medical/fatigue diagnosis — identifies workload patterns historically associated with reduced minutes or performance
- Moderate discriminative power (AUC-ROC ~0.62) — useful as a screening/ranking tool
- Temporal generalization may differ across seasons
- No GPS, heart rate, or subjective wellness data available
- Player roles shift during the season, changing their monitoring threshold
