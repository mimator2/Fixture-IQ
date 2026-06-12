# Fixture IQ Models

Trained machine learning models for player-match congestion and performance-risk monitoring. The repository contains two model families: **XGBoost V4B** (active, deployed in dashboard) and **CatBoost V6** (legacy, notebook experiments).

## Model Families

### XGBoost V4B (`XgBoost/`)

The production model deployed in the dashboard. A gradient-boosted decision-tree ensemble trained on 68,700+ player-match observations (2022–2025) to predict a binary **fatigue-performance risk** label.

- **Algorithm**: `XGBClassifier` (XGBoost 3.x)
- **Variant**: `v4b_no_competition` — excludes raw competition one-hot encoding for interpretability
- **Features**: 75 (74 numeric + 1 categorical `player_position`), 77 after one-hot expansion
- **Target**: `fatigue_performance_risk` = performance underperformance OR role-adjusted load reduction with fatigue context
- **Temporal split**: Train 2022 (5,749), Validation 2023 (6,479), Test 2024 (6,771)
- **Key metrics**:
  - AUC-ROC: 0.634
  - AUC-PR: 0.422 (1.38× over baseline 0.305)
  - Best F1 threshold: 0.435 (precision 0.351, recall 0.839)
- **Role-specific thresholds**: core_starter ≥ 0.45, rotation_player ≥ 0.50
- **Artifacts**: `fatigue_monitor/models/xgboost_v4b/` (model.pkl, preprocessor.pkl, metadata.json)
- **Training notebook**: `XgBoost/XG_Boost.ipynb`
- **Deployment**: loaded by `fatigue_monitor/src/prediction_v4b.py`, exported via `dashboard/export_data.py`

### CatBoost V6 (`CatBoostClassifier/`)

A complementary role-adjusted performance-risk model (legacy — not used by dashboard). Broader than V4B because it incorporates recent player form baselines (`avg_rating_last_3`, `avg_rating_last_5`) alongside workload features.

- **Algorithm**: `CatBoostClassifier`
- **Final variant**: `V6 No Competition` (100 features)
- **Sensitivity variant**: `V6 No Competition No Rating Baseline` (98 features, excludes form)
- **Target**: `v6_role_adjusted_fatigue_performance_risk`
- **Temporal split**: Train seasons < 2024, Test 2024
- **Key metrics (V6 No Competition)**:
  - AUC-ROC: 0.6753
  - AUC-PR: 0.4695
  - F1: 0.4842 (precision 0.4449, recall 0.5310)
- **Role-specific thresholds**: core_starter ≥ 0.50, rotation_player ≥ 0.60
- **Artifacts**: `CatBoostClassifier/outputs/` (.cbm model files, metadata, CSVs, PNGs)
- **Training notebook**: `CatBoostClassifier/CatBoost.ipynb`

**When to use which**: XGBoost V4B is the primary trainer-facing fatigue/workload score (active). CatBoost V6 is a legacy reference model not deployed in the dashboard.

## Directory Structure

```
models/
├── XgBoost/
│   └── XG_Boost.ipynb              # Training notebook with all version comparisons
│
└── CatBoostClassifier/
    ├── CatBoost.ipynb              # Training notebook
    └── outputs/                    # V4/V5/V6 artifacts, CSVs, PNGs
        ├── *.cbm                   # Serialised CatBoost models
        ├── *metadata.json          # Feature importances, policies
        ├── csvs/                   # Comparison tables, predictions
        └── pngs/                   # SHAP plots, threshold curves
```

Production artifacts are at `fatigue_monitor/models/xgboost_v4b/`.


## Key Design Choices

- **Temporal splitting**: both models train on past seasons and evaluate on the most recent season, preventing future leakage.
- **SHAP interpretability**: both models use TreeSHAP for global and local explanations.
- **Role-specific thresholds**: core starters and rotation players have different alert thresholds reflecting their different workload profiles.
- **No medical diagnosis**: both models are monitoring-support tools, not clinical fatigue detectors.

## Data Sources

- Master CSV: `Data/Fixture_IQ_Data_Seasons_2022-2025.csv` (~68,700 rows, 5 competitions, 3 seasons)
- Extraction: `Data_Extraction/` (API-Football + FBref pipelines)


*Last Updated: June 2026*
