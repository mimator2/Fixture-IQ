# Fixture IQ Models

This directory contains trained machine learning models and associated data for the Fixture IQ project.

## Models

### CatBoostClassifier - Player Performance Decrease Prediction

**Location**: `CatBoostClassifier/`

A predictive model that identifies players at risk of performance decline in their next match, enabling:
- Early injury prevention through targeted interventions
- Optimized squad rotation decisions
- Data-driven performance preservation

**Key Metrics**:
- AUC-ROC: 0.7714 (test set)
- F1-Score: 0.5986
- Catches 91% of true performance declines
- Only 24% false alarm rate

**Data Used**:
- 2,361 training matches (2022-2023 season)
- 674 test matches (2023-2024 season)
- 11 injury-related features
- 38 performance & workload features

See `CatBoostClassifier/README.md` for full documentation.

---

## Data Structure

```
models/
├── CatBoostClassifier/
│   ├── 01_player_performance_decrease_model.ipynb    (main notebook)
│   ├── README.md                                      (model documentation)
│   └── data/
│       ├── API/                          (multi-competition player/team stats)
│       │   ├── API_SEASON_2022_2023/     (CSVs for PL, CL, FA Cup, League Cup)
│       │   └── API_SEASON_2023_2024/
│       └── injuries/                     (processed injury data)
│           └── processed_injuries/       (injury spells, burden metrics)
```

---

## Quick Start

1. **View the Model**: Open `CatBoostClassifier/01_player_performance_decrease_model.ipynb`
2. **Understand the Data**: Check API and injury data in `CatBoostClassifier/data/`
3. **Review Results**: See SHAP analysis, threshold optimization, and performance metrics in notebook

---

## Data Sources

- **API Data**: Multi-competition player statistics extracted from official APIs
  - Premier League, Champions League, FA Cup, League Cup, Community Shield
  - Seasons: 2022-2023, 2023-2024
  
- **Injury Data**: Processed injury records from Transfermarkt
  - Individual injury timelines with recovery windows
  - Team-level injury burden metrics
  - Match-outcome injury data

---

## Model Architecture

**Algorithm**: CatBoostClassifier (Gradient Boosting)
- Handles categorical variables natively
- Feature importance via SHAP
- Balanced class weights for fairness
- 49 features (form + workload + injury + context)

**Target Variable**: Context-adjusted performance decrease
- Normalized for match difficulty and opponent strength
- Fair assessment independent of fixture type
- Binary classification (0 = maintain form, 1 = decline risk)

---

## Key Findings

1. **Form Dominance (71.5% importance)**: Recent performance is the strongest predictor
2. **Injury Matters (10.9% importance)**: Recovery status adds complementary signal
3. **Workload Effect (8.1% importance)**: Cumulative fatigue accumulates linearly
4. **Context Weak Effect (5.9% importance)**: Already captured by categorical features
5. **Regression to Mean**: High recent form increases decline risk (natural reversion)

---

## Deployment Status

✅ **Production Ready**
- Validated temporal generalization (2022-23 → 2023-24)
- Zero data leakage confirmed
- Fair predictions across match contexts
- SHAP interpretability for all predictions
- Optimal threshold identified (0.60)

⚠️ **Operational Integration Required**
- Combine with coaching expertise
- Real-time injury monitoring integration
- Quarterly model drift checks
- Annual retraining on new seasons

---

## Future Enhancements

Potential improvements (requiring additional data):
- Advanced injury severity scores
- Player aging/career stage factors
- Tactical system awareness
- Wearable sensor integration

---

For detailed documentation, see individual model READMEs.

*Last Updated: May 26, 2026*
