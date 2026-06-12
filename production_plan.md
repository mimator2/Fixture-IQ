# Production Readiness Plan

## 1. SHAP TreeExplainer — Main Risk Drivers

**Current**: `PlayerExplanation.jsx:4-52` uses hardcoded rules (weights assigned manually: `short_rest_matches_30d >= 2 → 100`, `full_90s_last_5 >= 4 → 79`, etc.)

**Target**: Use real SHAP values from the CatBoost model during export.

**Backend** (`prediction_v6.py`):
- After `model.predict_proba(X)`, add `shap.TreeExplainer(model).shap_values(X)`
- Store top-5 positive feature contributors per row as `shap_drivers_{suffix}` column

**Already available**: `shap==0.52.0` installed, `catboost==1.2.10` installed.

**Pipeline**: SHAP values flow through merge → `player_risks.json`

**Frontend** (`PlayerExplanation.jsx`):
- If `player.shap_drivers_perf` exists → render those directly
- Fallback to current rule-based `buildExplanations()`
- Update subtitle to `"— SHAP TreeExplainer feature contributions"`

**Concern**: SHAP on 61k rows may be slow. **Mitigation**: compute only for the latest snapshot rows (~1,189), not the full merged DataFrame.

---

## 2. Team Rotation — Falsy Check Bug

`TeamDetail.jsx:119` and `TeamGrid.jsx:59` use `team.overall_rotation_index ? ... : "—"`.
`0.0` is falsy → shows `"—"` for genuinely zero-rotation teams.
Fix: change to `team.overall_rotation_index != null ? ... : "—"`.

Files: `TeamDetail.jsx`, `TeamGrid.jsx` — 1 line each.

---

## 3. `days_since_last_injury` — Sentinel Bugs

| # | File | Bug | Fix |
|---|---|---|---|
| 1 | `export_data.py:306` | `(0 or -1) → -1` eats legitimate 0-day values | `int(val) if pd.notna(val) else None` |
| 2 | `SquadContextSection.jsx:26` | `(-1 ?? 99) < 21` → `true` (false positive) | `!= null && val < 21` |
| 3 | Both sections | Shows `"-1d"` for no-data players | Already ok: `!= null ? ... : null` → `"—"` once Python exports `None` |

Files: `export_data.py` (1 line), `SquadContextSection.jsx` (1 line).

---

## 4. Data Source — Info only

Full `Fixture_IQ_Data_Seasons_2022-2025.csv` (all 4 seasons) loaded. Post-prediction: PL teams only, historical data for those teams included in aggregates, per-player snapshots use most recent row.

---

## 5. "Avg. Rest Drop" — Info only

`StatsOverview.jsx:13-25`: `avgLowRest - avgMediumRest` = average rest days lost when congestion goes from Low (≥5d) to Medium (3-4d). Ignores High congestion.

**Optional**: Add Low → High drop stat.

---

## 6. RotationChart X-Axis — Team Names Clipping

`RotationChart.jsx:58`: 20 team names at `fontSize: 11`, horizontal → names clip.

Fix:
```jsx
<XAxis 
  dataKey="name" 
  tick={{ fontSize: 10 }} 
  angle={-45} 
  textAnchor="end" 
  interval={0}
  axisLine={false} 
  tickLine={false} 
/>
```

File: `RotationChart.jsx` — line 58.

---

## 7. Workload Timeline — Connect Data Pipeline

All pieces built except the data fetch:

| Piece | Status |
|---|---|
| Export generates `player_timelines/{key}.json` files | ✅ 1,203 files |
| `WorkloadTimeline.jsx` component | ✅ 50 lines |
| PlayerDetail opt-in toggle | ✅ Built, but shows "No timeline data" |
| **Fetch timeline file** | ❌ Missing — ~10 lines |

**Fix in `PlayerDetail.jsx`**: Add `useEffect` that fetches `player.id.json` from timeline dir when toggle is opened.
