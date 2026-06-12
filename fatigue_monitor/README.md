# Fatigue Monitor — XGBoost Model B v4b

Inference pipeline for the **XGBoost Model B v4b** fatigue-performance risk model. This is the **primary production model** deployed in the Fixture IQ dashboard. It predicts which players may be at elevated risk of reduced performance or managed minutes in their next fixture, based on rolling workload, multi-competition burden, and physical effort features.

> **Important**: This is a staff-support monitoring model, not a medical diagnosis tool. A positive flag indicates that the player's workload and recovery profile resemble situations historically associated with underperformance or managed minutes.

---

## Role in the Project

```
Data_Extraction/consolidation.py   →  data/Fixture_IQ_Data_Seasons_2022-2025.csv
                                            ↓
fatigue_monitor/src/
  feature_engineering_v4b.py       →  95 engineered features (75 used by model)
  prediction_v4b.py                →  risk scores, risk bands, monitoring flags
                                            ↓
dashboard/export_data.py           →  static JSON consumed by React frontend
```

`fatigue_monitor/` contains the **ML layer** of Fixture IQ:
- `src/config.py` — shared constants, paths, risk bands, feature groups
- `src/feature_engineering_v4b.py` — transforms raw match rows into model-ready features
- `src/prediction_v4b.py` — loads artifacts, runs inference, applies minute guard and thresholds
- `models/xgboost_v4b/` — serialized model, preprocessor, metadata, and operating policy


---

## Repository Structure

```
fatigue_monitor/
├── src/
│   ├── config.py                   # Paths, risk bands, thresholds, feature groups (V4B + V6)
│   ├── feature_engineering_v4b.py  # V4B feature pipeline (95 defined, 75 used)
│   ├── feature_engineering_v6.py   # Incomplete V6 pipeline (broken import)
│   ├── prediction_v4b.py           # Inference: load_v4b_artifacts(), predict_v4b()
│   ├── prediction_v6.py            # V6 inference (not used by dashboard)
│   └── __init__.py
│
└── models/
    ├── xgboost_v4b/                # Active V4B model artifacts
    │   ├── xgboost_model_b_v4b_final.pkl
    │   ├── xgboost_model_b_v4b_preprocessor.pkl
    │   ├── xgboost_model_b_v4b_numeric_features.pkl
    │   ├── xgboost_model_b_v4b_categorical_features.pkl
    │   ├── xgboost_model_b_v4b_metadata.json
    │   └── xgboost_model_b_v4b_operating_policy.json
    └── catboost_v6/                # Legacy CatBoost artifacts (not used)
```

---

## Config (`src/config.py`)

`config.py` is the single source of truth for paths, thresholds, and feature taxonomy. It is imported by `prediction_v4b.py`, `export_data.py`, and model metadata generators.

### Key constants

| Constant | Purpose |
|----------|---------|
| `V4B_MODEL_PATH` | Pickled XGBoost model |
| `V4B_PREPROCESSOR_PATH` | ColumnTransformer (imputer + OHE) |
| `V4B_NUM_FEATURES_PATH` | Ordered numeric feature names |
| `V4B_CAT_FEATURES_PATH` | Categorical feature names |
| `V4B_METADATA_PATH` | Feature importances, policy, groups |
| `V4B_POLICY_PATH` | Operating policy JSON |
| `V4B_RISK_BANDS` | `[0, 0.35, 0.45, 0.55, 1.01]` |
| `V4B_RISK_LABELS` | `["Low", "Medium", "High", "Very High"]` |
| `V4B_OPERATING_POLICY` | Default thresholds and messaging |

### Feature groups

`V4B_FEATURE_GROUPS` maps logical group names to feature lists. The full engineering superset is 95 features across 7 groups; the trained model uses 75. Empty groups (`missingness_context`, `recent_baseline_form`) are retained in metadata for documentation but contribute 0% importance.

---

## Feature Engineering (`feature_engineering_v4b.py`)

Takes raw player-match rows and produces 95 features in 7 groups. All features are computed **prior to the upcoming match** — no future leakage.

### Group summary

| Group | Defined | In model | Description |
|-------|---------|----------|-------------|
| workload_recovery_windows | 24 | yes | Rest days, ACWR, rolling minutes/starts/full-90s, short-rest sequences, congestion flags |
| competition_sequence_load | 26 | yes | UCL/cup minutes, European rest flags, competition transitions, days_since_european_match |
| recent_action_load | 19 | yes | Duels, tackles, fouls, dribbles last-3/14d, position z-scores, physical_load_index |
| injury_context | 9 | yes | Squad injury burden, returning_from_injury, injury_context_score |
| role_context | 4 | yes | player_position, player_role_v4b, is_home, is_substitute (OHE: G/D/M/F) |
| missingness_context | 11 | no | Binary missingness indicators for sparse features |
| recent_baseline_form | 2 | no | avg_rating_last_3, avg_rating_last_5 |

### Key design points

- **Minute guard**: rows with `minutes_played < 45` are flagged for downstream zeroing in prediction (not during feature engineering).
- **Role assignment**: players are classified as `core_starter` or `rotation_player` based on rolling starts/minutes, used for threshold selection.
- **Goalkeeper exclusion**: GKs are excluded from model inference at prediction time.
- **One-hot encoding**: categorical features (`player_position`, `player_role_v4b`) are expanded in the preprocessor; the exact output names are stored in `xgboost_model_b_v4b_categorical_features.pkl`.

---

## Prediction (`prediction_v4b.py`)

Exposes two main functions:

```python
from fatigue_monitor.src.prediction_v4b import load_v4b_artifacts, predict_v4b

metadata = load_v4b_artifacts()
results_df = predict_v4b(raw_match_df, metadata)
```

### Pipeline

1. **Load artifacts** — model, preprocessor, feature name lists, metadata, operating policy
2. **Enforce role-specific minute guard**:
   - `minutes_played < 45` → `risk_score = 0.0`
   - Goalkeepers → `risk_score = 0.0`
3. **Preprocess** — impute missing values, one-hot encode categoricals, align to model feature order
4. **Predict probabilities** — `model.predict_proba()` → probability of `fatigue_performance_risk`
5. **Assign risk band** — bin probability using `V4B_RISK_BANDS`
6. **Generate monitoring flag** — compare against `core_starter_threshold` or `rotation_player_threshold`
7. **Attach reasons** — human-readable strings from top feature drivers for the trainer output

### Thresholds and bands

| Band | Range | Core Starter Action | Rotation Player Action |
|------|-------|---------------------|------------------------|
| Low | 0 – 0.35 | Normal monitoring | Normal monitoring |
| Medium | 0.35 – 0.45 | Monitor response | Monitor response |
| High | 0.45 – 0.55 | Review minutes | Check wellness |
| Very High | 0.55 – 1.01 | Rest/recovery | Rest/recovery |

---

## Dashboard Export Integration

`dashboard/export_data.py` imports `config.py` paths directly to load V4B artifacts and to populate `model_metadata.json` with:
- `feature_importances` — XGBoost gain-weighted split contributions
- `feature_groups` — the `V4B_FEATURE_GROUPS` mapping from `config.py`
- `threshold_policy` — `V4B_OPERATING_POLICY` and role thresholds
- `risk_bands` and `risk_labels` — band boundaries and display names

This ensures the frontend and the inference pipeline share identical definitions.

---

## Relationship to Other Models

| Model | Purpose | Dashboard Role |
|-------|---------|----------------|
| XGBoost V4B | Workload/congestion risk (75 features) | **Primary** trainer-facing score |
| CatBoost V6 | Broader performance-risk (includes form baselines) | Legacy/not deployed |

The V4B model excludes recent rating baselines to produce a purer workload signal. This makes it more interpretable for coaching staff and more actionable for rotation decisions.

---

## Limitations

- Correlational, not causal — does not diagnose fatigue or predict injury
- 45-minute minimum excludes substitute cameos from training signal
- Player baselines are historical averages, not personalised random effects
- Confined to competitions and teams in the training set
- No GPS, heart rate, or subjective wellness data

---

*Last Updated: June 2026*
