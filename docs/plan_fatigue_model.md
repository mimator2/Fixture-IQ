# XGBoost Player Fatigue / Injury Risk Model — Plan

## Objective
Build an XGBoost classifier that, given a player's pre-match context, predicts whether they are at elevated fatigue/injury risk and need rest.

---

## Data Sources

| Source | Seasons | Teams | Granularity |
|--------|---------|-------|-------------|
| **SofaScore Dynamic** (`Data_Dynamic/`) | 24-25 (and extendable) | All PL + UCL teams | Player-level with engineered features: ACWR, rest_days, min_last_7d, SofaScore rating, high_congestion_flag |
| **FBref per-match reports** (`Data/SEASON_*/*/match_reports/`) | 22-23, 23-24, 24-25 | UCL-participant PL teams | Richer per-match stats: goals, assists, shots, tackles, interceptions, etc. |
| **SofaScore PL league-wide** (`Data/Premier_League/`) | 20-21 through 24-25 | ALL PL teams | Player & match data for non-UCL comparison |
| **SofaScore UCL** (`Data/Champions_League/`) | 20-21 through 24-25 | All UCL teams | Player & match data |
| **ClubElo** (`fixtureiq_elo_master.csv`) | Historical | All teams | Team strength over time |
| **Understat** (`fixtureiq_understat_master.csv`) | Historical | PL teams | xG, key passes, shot data |

### Teams per season (FBref, UCL-participant PL teams)

- **2022‑23**: Chelsea, Liverpool, Manchester City, Tottenham Hotspur
- **2023‑24**: Arsenal, Manchester City, Manchester United, Newcastle United
- **2024‑25**: Arsenal, Aston Villa, Liverpool, Manchester City

### Non-UCL PL teams (to add from SofaScore PL data)

From each season, teams that did **not** qualify for the Champions League — e.g. Brighton, Brentford, Crystal Palace, Fulham, Nottingham Forest, Wolves, Everton, West Ham, etc.

---

## Target Variable: `fatigue_risk`

Since we lack actual injury records, define a **composite proxy**:

`fatigue_risk = 1` if **≥ 2 of the following 3** are true:

1. **ACWR danger zone** — `acwr_ratio < 0.5` or `acwr_ratio > 1.5` (sports science injury risk thresholds)
2. **Performance decline** — SofaScore `rating` is > 1.0 points below the player's own 5-match rolling average rating
3. **High congestion** — `high_congestion_flag == 1` (rest ≤ 3 days)

---

## Features (all pre-match, no leakage)

### Workload / Fatigue
- `rest_days` — days since player's last match
- `high_congestion_flag` — binary: rest ≤ 3 days
- `min_last_7d` — minutes played in rolling 7-day window (acute load)
- `acwr_ratio` — acute:chronic workload ratio
- `consecutive_away_games` — travel burden proxy
- `lineup_churn` — squad rotation indicator

### Player Context
- `position` — categorical (D, M, F, G)
- `rating_rolling_avg_5` — player's 5-match average SofaScore rating (lagged)
- `rating_rolling_std_5` — variability in recent performance

### Match Context
- `is_away` — venue
- `competition` — Premier League, Champions League, FA Cup, EFL Cup
- `team_elo` — opponent strength proxy
- `team_xg`, `team_xga` — expected goals for/against

### UCL vs Non-UCL Comparison
- `is_ucl_team` — whether player's team participates in UCL that season
- `days_since_ucl_match` — recovery from European midweek fixture
- `total_team_matches_ytd` — team's total matches played that season (congestion measure)

---

## Model Architecture

- **Algorithm**: XGBoost Classifier
- **Handling imbalance**: `scale_pos_weight`, `class_weight` tuning
- **Cross-validation**: TimeSeriesSplit (no random shuffle — sequential match data)
- **Early stopping**: on validation AUC to prevent overfitting
- **Hyperparameter search**: `max_depth`, `learning_rate`, `n_estimators`, `subsample`, `colsample_bytree`, `reg_alpha`, `reg_lambda`

### Train / Validation / Test Split

| Set | Data |
|-----|------|
| **Train** | Season 2022‑23 + 2023‑24 |
| **Validation** | First half of 2024‑25 (Aug–Dec) |
| **Test** | Second half of 2024‑25 (Jan–May) |

---

## Comparison: UCL Teams vs Non-UCL Teams

1. Train separate models on UCL-only and non-UCL-only subsets
2. Compare:
   - Feature importance rankings (which signals matter most for each group?)
   - Prediction distributions (are UCL players flagged more often?)
   - Recall at different congestion levels
3. Key question: *Do UCL teams' players show different fatigue patterns, or does the extra fixture load push everyone past the same threshold?*

---

## Implementation Steps

### Phase 1 — Data Collection & Preparation
1. Identify non-UCL PL teams per season from SofaScore PL data
2. Extract/clean player-match data for non-UCL teams
3. Load all SofaScore Dynamic data with engineered features
4. Cross-reference FBref per-match reports for extra stats
5. Merge into unified dataset with consistent schema

### Phase 2 — Feature Engineering
1. Compute rolling player baselines (rating, workload)
2. Create composite target variable
3. Add team-level context features (UCL flag, total matches)
4. Encode categorical variables
5. Handle missing values (especially for first appearances)

### Phase 3 — Model Training
1. Time-series cross-validation pipeline
2. XGBoost training with early stopping
3. Hyperparameter tuning
4. Threshold tuning via precision-recall curve

### Phase 4 — Evaluation & Interpretation
1. Classification metrics (precision, recall, F1, AUC-ROC, AUC-PR)
2. Feature importance (gain, cover, frequency)
3. SHAP summary plots and dependence plots
4. Error analysis (false positives vs false negatives patterns)

### Phase 5 — Comparison Analysis
1. UCL teams vs non-UCL teams: model performance comparison
2. Feature importance differences between groups
3. Visualizations: SHAP comparison, prediction distributions, congestion impact

### Phase 6 — Deliverables
- `scripts/train_fatigue_model.py` — full training pipeline
- `scripts/predict_fatigue.py` — inference script
  - Usage: `python predict_fatigue.py --player "Bukayo Saka" --team "Arsenal" --season "2024-2025"`
  - Output: fatigue_risk probability + contributing factors
- `models/fatigue_xgb_model.json` — serialised model
- `models/feature_columns.json` — feature schema for inference
- `results/` — metrics, SHAP plots, comparison charts

---

## Additional Data Worth Exploring

| Source | Why |
|--------|-----|
| **Transfermarkt injury data** | Actual injury records (date, type, return date) — would validate the proxy target |
| **Travel distance** | km travelled between away matches — quantifies travel fatigue |
| **International break flag** | Players who played midweek internationals have extra load |
| **Weather conditions** | Match-day temperature / precipitation affects physical exertion |
| **Substitution timing** | Early subs may indicate planned load management |
