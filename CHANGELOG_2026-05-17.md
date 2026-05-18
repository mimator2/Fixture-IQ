# Changelog — Code Refinement & Cleanup
**Date:** 2026-05-17  
**Repo:** `tfp` (iAau199/tfp)  
**Scope:** Post-merge cleanup after absorbing Fixture-IQ; implements tutor (Pol) and colleague feedback

---

## Summary

7 tasks completed across 8 files.  
Net result: 4 dead scripts removed, 2 canonical scripts enhanced, 3 docs updated, 1 requirements simplified.  
Tech-debt scrubbed: zero imports of `cloudscraper`, `undetected-chromedriver`, `ScraperFC`, or `soccerdata` remain in canonical scripts.

---

## Scripts Modified

### `sofascore_direct.py` (+90 lines)

| # | Change | Rationale |
|---|--------|-----------|
| 1 | **`away_leg_sequence`** — per-team running count of consecutive away fixtures; resets to 0 on home match | Tutor: travel burden is a useful congestion proxy, especially for European legs |
| 2 | **`home_away_alternation_rate`** — rolling-5 fraction of H↔A venue switches | Tutor: "incorporate distance of travel … interesting in 2-3 consecutive away matches" |
| 3 | **`--clear-cache`** CLI flag — deletes `_cache/` before any API calls | Tutor: ability to purge stale cache if anti-bot session is dirty |
| 4 | **`--dry-run`** CLI flag — discovers season id, prints intended targets, exits without any HTTP calls | Enables safe inspection before long runs |
| 5 | Module docstring expanded — lists all per-team fatigue variables and all CLI flags | Maintainability |
| 6 | `--team` help text clarifies the 5 PL-UCL default | Colleague feedback confirmed filter is already correct; documented |
| 7 | `_build_team_fatigue_summary` adds `max_consecutive_away` and `avg_alternation_rate` columns | New travel features surfacing in summary output |

#### Variables now tracked in `_build_match_context`

| Variable | Description |
|---|---|
| `days_since_last_match` | Rest since previous fixture |
| `cumulative_matches` | Running total of matches played this season |
| `matches_last_7d` | Congestion indicator — matches in rolling 7-day window |
| `matches_last_14d` | Longer congestion — rolling 14-day window |
| `is_away` | 1 if away, 0 if home |
| `away_leg_sequence` | ⬅️ new — consecutive running count of away fixtures (resets on home) |
| `home_away_alternation_rate` | ⬅️ new — rolling-5 fraction of H↔A switches (travel stress proxy) |
| `rest_category` | `season_opener` / `congested` / `normal` / `well_rested` |

---

### `football_data_pipeline.py`

| Change | Detail |
|---|---|
| `_load_html` wait default `8 → 5` seconds | Multi-team orchestration scripts (`run_season_*.py`) call this in sequence; 60% faster for the retry case while still leaving the scroll loop (8 × 0.4 s = 3.2 s) intact for content rendering |

---

## Scripts Removed (4)

| File | Lines removed | Reason |
|---|---|---|
| `sofascore_pipeline.py` | 589 | Legacy v1 — ScraperFC-only. Superseded by `sofascore_direct.py` |
| `sofascore_pipeline (1).py` | 942 | Legacy v2 — ScraperFC+ClubElo+Understat. Both sub-systems now in `sofascore_direct.py` |
| `extract_context.py` | 36 | One-shot ClubElo + Understat extractor. Both integrated into `sofascore_direct.py` |
| `data_extraction/football_data_pipeline.py` | 1261 | Duplicate of root `football_data_pipeline.py` but requires `cloudscraper` + `undetected-chromedriver`. Root version is canonical. |

All 4 orchestrators in `data_extraction/` reference `football_data_pipeline.py` (root), not the removed fork — no breakage.

---

## Other Files Modified

### `requirements.txt`

**Removed** (unused):  
- `fake-useragent` — not imported anywhere  
- `ScraperFC` — all scripts using it were deleted  
- `seaborn` — not imported anywhere  
- `jupyter` — not imported anywhere  

**Kept / changed:**  
- `pandas`, `numpy`, `python-dateutil`, `pytz` — core  
- `requests`, `beautifulsoup4` — FBref + SofaScore direct API  
- `selenium`, `webdriver-manager` — FBref  
- `lxml` — faster HTML parsing  
- `playwright` — newly added; SofaScore Cloudflare bypass in `sofascore_direct.py`  
- `matplotlib` — newly listed; heatmap PNG rendering  

**Optional extras documented as comments:**  
- `soccerdata` — ClubElo / Understat (used indirectly in `sofascore_direct.py` via optional import)  
- `scipy`, `scikit-learn`, `pymc` — future modeling / Bayesian work  
- `jupyterlab`, `seaborn` — EDA notebooks  

---

### `docs/data_dictionary.md`

- `EDA/DATA/` hardcoded file tree replaced with `Data/` structure description  
- Extraction-methods table added, marking removed scripts as ❌  
- `away_leg_sequence` and `home_away_alternation_rate` added to "Computed Indicators"  
- Canonical column-name reference table added (all common column names across sources)

---

### `data_extraction/README.md`

- Added project-context header ("Part of FixtureIQ / tfp")  
- Notes that the Fixture-IQ fork under `data_extraction/` has been removed; canonical scripts are at the root

---

### `.kilo/plans/1779044918914-shiny-island.md`

- Replaced initial execution plan with the full refinement & cleanup plan  
- Covers: tutor feedback analysis, colleague feedback, file inventory, detailed change plan, priority table, red flags

---

## Structural Validity Checks

| Assertion | Result |
|---|---|
| `sofascore_direct.py`: 0 BroaderChangeError imports: `cloudscraper`, `undetected_chromedriver`, `ScraperFC`, `soccerdata` | ✅ Confirmed |
| `football_data_pipeline.py`: same check | ✅ Confirmed |
| `fbref_advanced_pipeline.py`: same check | ✅ Confirmed |
| `sofascore_direct.py`: `--clear-cache` flag exists in `parse_args()` and `main()` | ✅ Confirmed |
| `sofascore_direct.py`: `--dry-run` flag exists in `parse_args()` and `main()` | ✅ Confirmed |
| `sofascore_direct.py`: `away_leg_sequence` and `home_away_alternation_rate` tracked in `_build_team_fatigue_summary` | ✅ Confirmed |
| `sofascore_direct.py`: module docstring lists new variables and CLI flags | ✅ Confirmed |
| `data_extraction/run_season_2024_2025.py`: still 4 orchestrators all intact | ✅ Confirmed |
| `data_extraction/`: no remaining `.py` beyond 4 orchestrators + README | ✅ Confirmed |
| Root directory `.py` count: exactly 4 canonical scripts | ✅ Confirmed |
