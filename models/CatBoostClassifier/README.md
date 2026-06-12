# CatBoost Role-Adjusted Performance-Risk Models

## Overview

This directory contains the CatBoost modelling workflow for predicting player-match observations associated with future performance decrease, managed involvement, and workload-associated performance risk.

The final CatBoost framework evolved from an initial player performance decrease model into a broader **role-adjusted performance-risk modelling pipeline**. The strongest final model is:

```text
CatBoost V6 No Competition
```

This model predicts whether a player is at increased risk of future underperformance or managed minutes using recent form, role context, workload history, action-load, recovery, competition-sequence burden, and injury context.

Importantly, the final CatBoost V6 model should be interpreted as a:

```text
Role-adjusted workload-associated performance-risk model
```

It should **not** be interpreted as a definitive physiological fatigue diagnosis model.

---

## Final Model Family

The notebook contains multiple CatBoost model generations and outputs:

| Model Stage                             | Purpose                                                       |
| --------------------------------------- | ------------------------------------------------------------- |
| Early CatBoost models                   | Baseline performance-decrease prediction                      |
| Model D / v4b strict                    | Stricter performance-decrease and fatigue-associated variants |
| V5 fatigue-associated model             | Broad fatigue-associated decline baseline                     |
| V6 role-adjusted model                  | Final role-adjusted performance-risk framework                |
| V6 no-rating-baseline sensitivity model | Cleaner fatigue/workload sensitivity analysis                 |

The final selected operational CatBoost model is:

```text
V6 No Competition
```

A sensitivity model was also trained:

```text
V6 No Competition No Rating Baseline
```

---

## Final CatBoost V6 Model Specification

* **Algorithm**: CatBoostClassifier
* **Final model**: `V6 No Competition`
* **Target**: `v6_role_adjusted_fatigue_performance_risk`
* **Task**: Binary classification
* **Training seasons**: Seasons before 2024
* **Evaluation season**: 2024
* **Final modelling population**:

  * Outfield players only
  * Scorable appearances
  * Core starters and rotation players
  * Excludes rare players and impact substitutes from the main modelling population
* **Final feature count**: 100
* **Raw competition label used by final model**: No

---

## Final V6 Performance

| Model               | Features |  AUROC | PR-AUC |     F1 | Precision | Recall | Balanced Accuracy |
| ------------------- | -------: | -----: | -----: | -----: | --------: | -----: | ----------------: |
| V6 Keep Competition |      101 | 0.6761 | 0.4721 | 0.4842 |    0.4319 | 0.5509 |            0.6349 |
| V6 No Competition   |      100 | 0.6753 | 0.4695 | 0.4842 |    0.4449 | 0.5310 |            0.6370 |

The **V6 No Competition** model was selected because it achieved nearly identical ranking performance to the keep-competition variant while slightly improving precision and balanced accuracy. It was also preferred because it avoids direct dependence on broad raw competition labels.

---

## Sensitivity Analysis: Removing Recent Rating Baseline

Because the full V6 model was strongly influenced by recent rating-baseline features, a sensitivity model was trained without:

```text
avg_rating_last_3
avg_rating_last_5
```

| Model                                | Uses Recent Rating Baseline | Features |  AUROC | PR-AUC |     F1 | Precision | Recall | Balanced Accuracy |
| ------------------------------------ | --------------------------- | -------: | -----: | -----: | -----: | --------: | -----: | ----------------: |
| V6 No Competition                    | Yes                         |      100 | 0.6753 | 0.4695 | 0.4842 |    0.4449 | 0.5310 |            0.6370 |
| V6 No Competition No Rating Baseline | No                          |       98 | 0.6079 | 0.3847 | 0.4133 |    0.3742 | 0.4615 |            0.5811 |

Removing recent rating baseline reduced performance, confirming that recent form is an important driver of the full V6 model.

However, the no-rating-baseline model still retained meaningful predictive ability. This shows that workload, recovery, role, action-load, calendar congestion, and injury-context features also carry independent signal.

---

## Improvement Over V5

Compared with the V5 fatigue-associated decline baseline, the final V6 model improved substantially across most metrics.

| Model                         |  AUROC | PR-AUC |     F1 | Precision | Recall | Balanced Accuracy |
| ----------------------------- | -----: | -----: | -----: | --------: | -----: | ----------------: |
| V5 Fatigue-Associated Decline | 0.5910 | 0.3162 | 0.4088 |    0.3168 | 0.5762 |            0.5826 |
| V6 No Competition             | 0.6753 | 0.4695 | 0.4842 |    0.4449 | 0.5310 |            0.6370 |

V6 improved AUROC, PR-AUC, F1-score, precision, and balanced accuracy. Recall decreased slightly, meaning V6 became more selective, but the alerts became more reliable.

---

## Role-Specific Threshold Policy

V6 uses role-specific monitoring thresholds because core starters and rotation players have different expected workload patterns.

The final threshold policy is:

| Player Role     | Threshold |
| --------------- | --------: |
| Core starter    |      0.50 |
| Rotation player |      0.60 |

This policy achieved the following performance on the 2024 temporal evaluation set:

| Metric            |  Value |
| ----------------- | -----: |
| Precision         | 0.4477 |
| Recall            | 0.5310 |
| F1                | 0.4858 |
| Balanced Accuracy | 0.6385 |
| Alerts            |    478 |
| Alert Rate        |  33.1% |

Confusion matrix:

|               | Predicted Low Risk | Predicted Monitoring Flag |
| ------------- | -----------------: | ------------------------: |
| True Low Risk |                775 |                       264 |
| True Risk     |                189 |                       214 |

Because the final V6 modelling population is dominated by core starters, this should mainly be interpreted as a **core-starter monitoring policy**, with the rotation-player threshold retained for future scalability.

---

## Feature Importance Summary

The selected V6 model was strongly influenced by recent baseline form.

| Feature Group                                    | Importance |
| ------------------------------------------------ | ---------: |
| Recent baseline form                             |     55.51% |
| Rolling match workload / other workload features |      8.62% |
| Position-adjusted load                           |      8.05% |
| Recent action load                               |      7.78% |
| Workload/recovery windows                        |      6.50% |
| Role context                                     |      6.36% |
| Competition-sequence load                        |      4.17% |
| Injury context                                   |      2.86% |
| Missingness context                              |      0.16% |

The strongest individual features were:

| Feature                          | Importance | Interpretation                          |
| -------------------------------- | ---------: | --------------------------------------- |
| `avg_rating_last_3`              |      39.91 | Recent short-term performance baseline  |
| `avg_rating_last_5`              |      15.60 | Recent medium-term performance baseline |
| `shots_last_5`                   |       4.74 | Recent attacking action-load            |
| `full_match_exposure_last_5`     |       2.60 | Recent full-match workload              |
| `all_comp_minutes_pressure`      |       2.35 | Accumulated match-load pressure         |
| `ucl_minutes_last_21d`           |       1.98 | Recent European competition burden      |
| `dribbles_attempts_last_5_pos_z` |       1.95 | Position-adjusted attacking action-load |
| `appearances_last_5`             |       1.88 | Recent match involvement                |
| `minutes_median_last_5`          |       1.65 | Recent role/minutes profile             |
| `minutes_last_5_matches_pos_z`   |       1.56 | Position-adjusted recent minutes        |

The dominance of recent baseline form means that the full V6 model should be interpreted as a broad performance-risk model with fatigue/workload context, not as a pure workload-only fatigue model.

---

## Main Feature Families

The final V6 feature set includes:

### Role Context

* `player_position`
* `player_role_v6`
* `is_substitute`
* `start_flag`
* `minutes_median_last_5`
* `minutes_median_last_10`
* `starts_last_10_matches`
* `appearances_last_10_matches`
* `avg_minutes_last_10`

### Workload and Recovery

* `rest_days`
* `acwr_ratio`
* `min_last_7d`
* `min_last_14d`
* `min_last_21d`
* `min_last_28d`
* `starts_last_7d`
* `starts_last_14d`
* `starts_last_28d`
* `full_90s_last_7d`
* `full_90s_last_14d`
* `full_90s_last_28d`
* `matches_with_rest_le_3d_last_30d`
* `matches_with_rest_le_4d_last_30d`
* `matches_with_rest_le_6d_last_30d`

### Competition-Sequence Load

The final selected model does not use the raw `competition_type` feature, but it does use engineered competition-sequence workload variables such as:

* `ucl_minutes_last_7d`
* `ucl_minutes_last_14d`
* `ucl_minutes_last_21d`
* `ucl_matches_last_30d`
* `cup_minutes_last_7d`
* `cup_minutes_last_14d`
* `cup_matches_last_30d`
* `days_since_european_match`
* `post_ucl_short_rest`
* `pl_after_ucl_with_short_rest`

### Recent Action Load

* `shots_last_5`
* `key_passes_last_5`
* `tackles_last_5`
* `interceptions_last_5`
* `dribbles_attempts_last_5`
* `duels_total_last_5`
* `fouls_committed_last_5`
* `recent_action_load_score`
* `high_recent_action_load_by_position`

### Position-Adjusted Load

* `minutes_last_5_matches_pos_z`
* `minutes_last_3_matches_pos_z`
* `min_last_7d_pos_z`
* `all_comp_minutes_pressure_pos_z`
* `recent_action_load_score_pos_z`
* `shots_last_5_pos_z`
* `key_passes_last_5_pos_z`
* `tackles_last_5_pos_z`
* `interceptions_last_5_pos_z`
* `dribbles_attempts_last_5_pos_z`
* `duels_total_last_5_pos_z`

### Injury Context

* `squad_injured_count`
* `squad_soft_tissue_count`
* `squad_avg_days_out`
* `fixtures_missed_last_30d`
* `fixtures_missed_last_90d`
* `returning_from_injury`
* `days_since_last_injury`
* `recent_injury_return_flag`
* `medium_recent_injury_return_flag`
* `long_recent_injury_history_flag`
* `missed_recent_fixture_flag`
* `missed_multiple_recent_fixtures_flag`
* `missed_fixtures_90d_pressure`
* `high_squad_injury_pressure`
* `high_soft_tissue_pressure`
* `long_squad_absence_pressure`
* `squad_injury_high_workload`
* `soft_tissue_pressure_high_load`
* `injury_context_score`

### Missingness Indicators

V6 uses missingness-aware fatigue handling. Missingness indicators were created before imputation for key workload, recovery, and injury-context variables.

Examples include:

* `rest_days_missing`
* `squad_injured_count_missing`
* `squad_soft_tissue_count_missing`
* `squad_avg_days_out_missing`
* `days_since_last_injury_missing`
* `fixtures_missed_last_30d_missing`
* `fixtures_missed_last_90d_missing`
* `returning_from_injury_missing`
* `acwr_ratio_missing`
* `min_last_7d_missing`
* `days_since_european_match_missing`

---

## Data Leakage Controls

The notebook applies leakage controls by excluding future outcome variables, target-construction variables, and shortcut columns from model training.

Excluded variables include:

* `next_api_rating`
* `next_minutes_played`
* `performance_residual_v6`
* `performance_underperformance_v6`
* `role_adjusted_load_reduction_v6`
* `v6_fatigue_context_signal`
* previous target columns
* final target columns
* raw identifiers
* direct current-match performance outcomes
* broad team identity shortcuts

The final selected model also removes raw `competition_type` to reduce dependence on broad competition labels.

---

## Trainer Output

The notebook generates a trainer-facing output table for the 2024 temporal evaluation season.

The trainer output includes:

* player identity
* match context
* role classification
* workload and recovery indicators
* competition-sequence burden
* injury context
* V6 risk score
* role-specific monitoring flag
* risk band
* human-readable reason string

The main trainer output file is:

```text
outputs/csvs/v6_role_adjusted_trainer_output.csv
```

This output is intended for monitoring and review, not automatic rest decisions.

---

## Operational Interpretation

A positive V6 flag should be interpreted as:

```text
This player should be reviewed because their workload, rest pattern, action load, role context, competition sequence, and injury context resemble situations historically associated with underperformance or managed minutes.
```

A positive flag does **not** mean that the player must automatically be rested.

The model should support, not replace:

* coaching judgement
* medical assessment
* player communication
* GPS and physical tracking data
* tactical context
* match importance
* subjective wellness information

---

## Recommended Dashboard Design

The final comparison with XGBoost Model B v4b suggests a two-score dashboard design.

| Dashboard Score              | Model                              | Purpose                                               |
| ---------------------------- | ---------------------------------- | ----------------------------------------------------- |
| Fatigue/workload risk score  | XGBoost Model B v4b No Competition | Main trainer-facing role-adjusted workload-risk score |
| Broad performance-risk score | CatBoost V6 No Competition         | Secondary analyst-facing performance-risk context     |

This separates two different questions:

```text
Does this player’s workload, recovery profile, fixture congestion, competition burden, and squad context suggest monitoring or rest consideration?
```

and:

```text
Is this player also at broader risk of underperformance or managed involvement, considering recent form and role context?
```

---

## Files in This Directory

```text
01_player_performance_decrease_model.ipynb
README.md
outputs/
```

### Main model artifacts

```text
outputs/v6_role_adjusted_catboost_model.cbm
outputs/v6_role_adjusted_model_metadata.joblib
outputs/v6_role_adjusted_model_metadata.json
outputs/v6_no_comp_no_rating_model.cbm
outputs/v6_no_comp_no_rating_metadata.joblib
outputs/v6_no_comp_no_rating_metadata.json
```

### Main V6 CSV outputs

```text
outputs/csvs/v6_model_comparison.csv
outputs/csvs/v6_feature_importance.csv
outputs/csvs/v6_feature_group_importance.csv
outputs/csvs/v6_role_specific_threshold_optimization.csv
outputs/csvs/v6_role_adjusted_trainer_output.csv
outputs/csvs/v6_sensitivity_rating_baseline_comparison.csv
```

### V5 comparison outputs

```text
outputs/csvs/v5_model_comparison_vs_v4b.csv
outputs/csvs/v5_fatigue_associated_feature_importance.csv
outputs/csvs/v5_fatigue_associated_feature_group_importance.csv
outputs/csvs/v5_operational_trainer_thresholds.csv
outputs/csvs/v5_fatigue_associated_trainer_output_validation.csv
outputs/csvs/v5_fatigue_associated_trainer_output_deployment.csv
```

### Additional outputs

```text
outputs/pngs/
outputs/models/
outputs/csvs/
```

---

## Model Limitations

Important limitations:

* The full V6 model is strongly influenced by recent rating baseline.
* It should not be interpreted as a pure physiological fatigue model.
* The 2024 evaluation season was also used as the CatBoost early-stopping evaluation set.
* The rotation-player group is small, so the rotation-specific threshold should be treated cautiously.
* The model does not include GPS, wellness, sleep, or direct medical screening data.
* Predictions should be combined with staff expertise before operational decisions.
* External validation on additional clubs, competitions, and seasons is still required.

---

## Production Recommendation

The final CatBoost V6 model is useful as a broad performance-risk monitoring model.

Recommended usage:

| Use Case                                                | Recommendation                             |
| ------------------------------------------------------- | ------------------------------------------ |
| Broad performance-risk monitoring                       | Use `V6 No Competition`                    |
| Cleaner fatigue/workload sensitivity interpretation     | Use `V6 No Competition No Rating Baseline` |
| Trainer-facing fatigue/workload dashboard primary score | Prefer XGBoost Model B v4b No Competition  |
| Analyst-facing secondary performance-risk score         | Use CatBoost V6 No Competition             |

The final CatBoost V6 model is ready for analyst-facing decision support, but it should be deployed with clear interpretation labels and not presented as a direct fatigue diagnosis system.

---

## Final Interpretation

The final CatBoost V6 model is best described as:

```text
A role-adjusted workload-associated performance-risk model
```

It combines:

* recent form
* workload accumulation
* recovery time
* competition-sequence pressure
* action-load
* position-adjusted load
* injury context
* player role

into a single monitoring score.

Its main value is helping analysts and performance staff prioritize player-match observations for review before the next fixture.

---

*Last Updated: June 2026*
*Model Version: CatBoost V6 No Competition*
*Sensitivity Model: CatBoost V6 No Competition No Rating Baseline*

