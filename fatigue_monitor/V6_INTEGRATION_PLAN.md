# V6 CatBoost Integration Plan

## Architecture

- **Two V6 CatBoost models** loaded alongside existing XGBoost v4b
- **Fatigue/Workload Score** (primary) = V6 No Competition No Rating Baseline — clean fatigue/workload/action-load signal
- **Performance-Risk Score** (secondary) = V6 No Competition — includes rating-baseline regression signal
- Both scores shown side by side in the dashboard

## Model Files

```
models/catboost_v6/
  v6_no_competition/
    model.cbm            ← v6_role_adjusted_catboost_model.cbm
    metadata.joblib      ← v6_role_adjusted_model_metadata.joblib
  v6_no_rating_baseline/
    model.cbm            ← v6_no_comp_no_rating_model.cbm
    metadata.joblib      ← v6_no_comp_no_rating_metadata.joblib
```

## Files to Create

### src/feature_engineering_v6.py
V6-specific features built on top of existing `engineer_features()` base:
1. **start_flag** — binary: was player a starter?
2. **Missingness indicators** (11 binary flags) — one per feature that may be NaN
3. **Competition flags** — is_champions_league, is_european_fixture, is_domestic_cup, is_league
4. **Per-player rolling features** (single numpy pass per player):
   - starts_last_5, appearances_last_5, starts_last_10_matches, appearances_last_10_matches
   - avg_minutes_last_5, avg_minutes_last_10
   - minutes_last_3_matches (sum), minutes_last_5_matches (sum)
   - managed_minutes_last_5 (count < 60 min), full_match_exposure_last_5 (count >= 85 min)
   - shots_last_5, key_passes_last_5, tackles_last_5, interceptions_last_5
   - dribbles_attempts_last_5, duels_total_last_5, fouls_committed_last_5 (sum per column)
   - avg_rating_last_3, avg_rating_last_5 (shifted rolling mean)
5. **Composite scores**:
   - all_comp_minutes_pressure = minutes_last_5 / (appearances_last_5 * 90)
   - recent_action_load_score = sum of all action columns last 5
   - recent_action_load_per90 = recent_action_load_score / minutes_last_5 * 90
   - high_recent_action_load_by_position = flag if per90 pos_z > 1.0
6. **Position-adjusted Z-scores** (13 features — per-position z-score of rolling features)
7. **Injury context** (13 flags from squad/player injury data)
8. **injury_context_score** — count of active injury flags
9. **assign_player_role_v6()** — core_starter if starts_last_5 >= 3 and avg_minutes_last_5 >= 70

### src/prediction_v6.py
```python
load_v6_model(variant)       → CatBoost model + metadata
predict_v6(df_raw, model, metadata) → df with risk_score, threshold, flag, band, reasons
_generate_v6_reasons(df, metadata)  → main risk reason strings
```

## Files to Modify

### src/config.py
Add V6 model paths, V6_OPERATING_POLICY, V6_RISK_BANDS/LABELS/COLORS constants.

### Home.py
- Cache-load both V6 models
- Call predict_v6() for both variants
- Store results_df with v4 + both v6 score columns

### views/team_overview.py
- Dual-score columns in table
- V6 risk badges + reasons
- Both sets of filters/metrics

### views/player_detail.py
- V6 gauge chart
- Workload context metrics
- V6 main risk reasons as badges
- Fix back-button target from app.py → Home.py

### views/model_explain.py
- V6 feature importance section
- Side-by-side V4 vs V6 metrics

### views/about.py
- Document two-score system
- Both models' performance metrics

## Risk System (shared by both V6 variants)

| Risk Band | Range      | Threshold Check        |
|-----------|------------|------------------------|
| Low       | 0.00-0.25  | Clear                  |
| Medium    | 0.25-0.45  | Clear (< threshold)    |
| High      | 0.45-0.65  | Monitor (≥ threshold)  |
| Very High | > 0.65     | Monitor (≥ threshold)  |

| Role               | Threshold |
|--------------------|-----------|
| core_starter       | 0.50      |
| rotation_player    | 0.50      |

## Verification
- `streamlit run fatigue_monitor/Home.py --server.port 8504` — clean startup, no import errors
- All sidebar pages render without crashes
- Both V6 models load and predict without errors
- Dual scores visible in team overview and player detail
