# Fixes Plan — Fixture IQ Dashboard

## 1. Fix Squad Risk Distribution legend text visibility
**File:** `dashboard/src/components/risk/TeamRiskSummary.jsx`
- Change `Legend wrapperStyle={{ fontSize: 12 }}` to include `color: "hsl(var(--foreground))"` so legend text is visible on dark blue backgrounds

## 2. Center Top Global Model Features chart
**File:** `dashboard/src/pages/ModelExplanation.jsx`
- Reduce `margin.left` from 200 → 160
- Reduce `YAxis width` from 190 → 150
- Increase `margin.right` from 40 → 80
This better balances the chart area within the card.

## 3. Better describe Congestion Impact Radar
**File:** `dashboard/src/pages/TeamDetail.jsx` line 149
- Replace `"Normalized metrics across congestion levels"` with:
  `"Shows how performance (points, xG, win rate) changes across Low/Medium/High fixture congestion, alongside squad rotation rate — values are min-max normalized (0–100) per metric for comparison across levels"`

## 4. Fix `is_substitute` comparison (causes 0.0 rotation for all teams)
**File:** `dashboard/export_data.py` lines ~313 and ~361
- **Bug:** `.astype(str) == "False"` fails because `is_substitute` in the `merged` DataFrame is likely integer (0/1) after pandas operations. `.astype(str)` converts 0 → `"0"` and 1 → `"1"`, neither matching `"False"`, so no starters are ever counted → `overall_rotation_index = 0.0` for all teams.
- **Fix both occurrences:** Replace `grp[grp["is_substitute"].astype(str) == "False"]` with `grp[~grp["is_substitute"].astype(bool)]`
  - Handles: bool (True/False), int (0/1), and string ("True"/"False") correctly
- **After fix:** Re-run `python export_data.py` to regenerate `teams.json` and `congestion_metrics.json`

## 5. Confirm single-season filter
**File:** `dashboard/export_data.py` lines 172–176
- Code already filters to latest season only: `latest_season = df["season"].max()` → Premier League teams only
- **Issue:** `teams.json` shows `"season": "2022-23"` for all teams, not `"2024-25"`. This is because the `season` field (line 323–325) reads `grp["season"].iloc[0]` from the original grouped data which still contains multi-season data for PL teams that were also in the PL in earlier seasons. The first season encountered may not be the latest.
- **Fix:** Use `latest_season` instead of `grp["season"].iloc[0]` for the team's season field

## 6. Fix PlayerDetail crash ("all blue")
**File:** `dashboard/src/pages/PlayerDetail.jsx`
- **Root cause:** `useMemo(() => ..., [player.id])` on lines ~132 and ~137 can cause a **Rules of Hooks violation**: `useMemo` called conditionally inside JSX (only reached when `player` is truthy). React expects hooks in the same order every render — skipping them on some renders throws off the call order, potentially causing crashes or warnings in development mode.
- **Fix:** Move both `useMemo` calls to top-level variables **before** the early return, using `player?.id` as dependency:
  ```javascript
  const playerExplanation = useMemo(
    () => player ? <PlayerExplanation player={player} /> : null,
    [player?.id]
  );
  const sectionsGrid = useMemo(
    () => player ? (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <WorkloadSection player={player} />
        <CompetitionSection player={player} />
        <PhysicalEffortSection player={player} />
        <SquadContextSection player={player} />
      </div>
    ) : null,
    [player?.id]
  );
  ```
  Then use `{playerExplanation}` and `{sectionsGrid}` inside the JSX return, replacing the inline `{useMemo(...)}` calls.

## Execution Order
1. Fix PlayerDetail (crash fix — most impactful)
2. Fix `export_data.py` `is_substitute` comparison + season display
3. Fix TeamRiskSummary Legend color
4. Fix ModelExplanation margins
5. Fix TeamDetail radar description
6. Re-run `python export_data.py` to regenerate data files
7. Verify build passes (`npm run build`)
8. Verify rotation values are non-zero after data re-export
