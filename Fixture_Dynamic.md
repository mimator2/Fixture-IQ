# FixtureIQ Dynamic Congestion Pipeline: Architectural Deep Dive

## Executive Summary
The `FixtureIQDynamicPipeline` is an automated sports science data engineering asset designed to quantify fatigue metrics and workload congestion across elite professional football squads. 

The pipeline dynamically isolates a target cohort of Premier League clubs, aggregates their multi-competition schedules (including domestic leagues, domestic cups, and continental tournaments), extracts micro-level player performance match sheets via `ScraperFC` (SofaScore endpoints), and blends static historical contextual difficulty metrics using `SoccerData` (`ClubElo`) by calculating chronological validity boundaries.

---

## 1. Core Architectural Pillars

The script is built on four functional engineering concepts:
[ Dynamic Discovery ] ➔ [ Multi-Tournament Crawl ] ➔ [ Time-Series Cache ] ➔ [ Chronological Interval Alignment ]

### Dynamic Discovery
Rather than relying on hardcoded arrays of teams that risk deprecation due to annual league promotion and relegation, the pipeline queries the primary tournament (`England Premier League`) first. It scans all match objects within the requested season to dynamically extract a unique set of competing club strings, ensuring 100% year-over-year compatibility.

### Multi-Tournament Crawl
The pipeline avoids tournament-centric data siloing. It evaluates players across a complete chronological match stream encompassing:
* **Domestic Leagues:** `England Premier League`
* **Continental Competitions:** `UEFA Champions League`, `UEFA Europa League`, `UEFA Conference League`
* **Domestic Cups:** `FA Cup`, `EFL Cup`

### Resilience and Anti-Ban Design
Scraping micro-level player data match-by-match requires massive iterative request cycles. The pipeline implements two protective mechanisms:
1. **Dynamic Throttle Delay:** Explicitly introduces a polite pacing block (`self.delay`) between network calls to mitigate the risk of temporary IP banning or Cloudflare protection triggers.
2. **Anti-Ban File System Cache:** Every successfully parsed match sheet is written to a hidden directory (`.fixtureiq_cache/match_{id}.csv`). If a run crashes or if the code is re-executed, it reads directly from the local disk at lightning speed, minimizing API latency and infrastructure load.

---

## 2. Mathematical & Feature Engineering Formulations

Once the comprehensive multi-competition dataset is sorted chronologically by player and date, the pipeline derives time-series variables to model acute physical load and fatigue-induced performance degradation.

### Rest Days ($R_t$)
Calculates the consecutive calendar rest window available to an individual player prior to kick-off at match time $t$.
$$R_t = \text{Date}_t - \text{Date}_{t-1}$$
*If no prior match context exists within the seasonal scope, a rested baseline default of 14 days is automatically imputed.*

### High Congestion Indicator Flag ($C_t$)
A binary classification feature identifying extreme fixture congestion, which sports medicine literature notes as an elevated injury risk window.
$$C_t = \begin{cases} 1, & \text{if } R_t \le 3 \text{ days} \\ 0, & \text{otherwise} \end{cases}$$

### Rolling Workload Windows (7-Day and 28-Day Fatigue Maps)
To capture systemic physical exertion, the pipeline builds dynamic rolling window aggregates that look backward from the current fixture date (excluding the match currently being played, via `closed='left'`).
* **Acute Minutes Window ($\text{Min}_{7d}$):** Captures the absolute minutes played in the preceding 7 days, reflecting immediate physical fatigue.
* **Chronic Minutes Window ($\text{Min}_{28d}$):** Captures the absolute minutes played in the preceding 28 days, reflecting built-up fitness and workload tolerance.

### Acute-to-Chronic Workload Ratio ($\text{ACWR}$)
The pipeline implements the standard sports analytics benchmark for injury prevention—the Acute-to-Chronic Workload Ratio. It divides the acute 7-day workload by the average weekly workload over a rolling 4-week chronic window.
$$\text{ACWR}_t = \frac{\text{Min}_{7d}(t)}{\left(\frac{\text{Min}_{28d}(t)}{4.0}\right)}$$
* An $\text{ACWR}$ within the range of `0.8 - 1.3` is generally considered a stabilized fitness "sweet spot," while values exceeding `1.5` represent an acute workload spike (injury danger zone).

### Standardized Efficiency Normalization
1. **Duel Success Percentage:**
$$\text{Duel \%} = \frac{\text{duelsWon}}{\text{duelsWon} + \text{duelsLost}} \times 100$$
2. **Turnovers Normalized Per 90 Minutes:**
$$\text{Turnovers}_{90} = \frac{\text{possessionLostCtrl}}{\text{minutesPlayed}} \times 90$$

---

## 3. Structural Step-by-Step Code Walkthrough

### `__init__` Initialization
Prepares file paths, handles target directory generation (`Data_Dynamic` and `.fixtureiq_cache`), and instantiates the `ScraperFC.Sofascore()` selenium/botasaurus driver package wrapper under forced execution environments (Microsoft Edge execution binary flags).

### `discover_pl_teams()`
Queries the standard `England Premier League` match dictionary index. Iterates through the matches to identify all participating top-flight clubs, returning a sanitized hash set of team name strings.

### `build_universal_fixtures()`
Iterates through every competition listed in `COMPETITIONS_POOL`. It extracts match schedule dictionaries, tests if either competing side belongs to the discovered Premier League club set, attaches metadata tracking tags (`_target_competition`), and returns a globally unified schedule array sorted chronologically by Unix timestamp.

### `execute_pipeline()`
The master controller function that executes the scheduling sequence, orchestrates the cached web scraping loop, concatenates the resulting dataframes, and applies the pandas rolling calculations to construct the time-series model features.

### Advanced SoccerData ClubElo Interval Alignment
Because ClubELO ratings represent a fluid timeline tracking team strength over ranges of dates (marked by `from` and `to` columns) rather than static, fixed entries, the pipeline implements an interval alignment loop. 

1. It flattens the SoccerData MultiIndex and maps the 20 unique SofaScore club string variants over to colloquial ClubELO keys (e.g., mapping `"Brighton & Hove Albion"` to `"Brighton"`, and `"Wolverhampton"` to `"Wolves"`).
2. It loops through each team's matches and checks for rows where the match date falls between the historical validity boundaries:
$$\text{df\_elo['from']} \le \text{Match Date} \le \text{df\_elo['to']}$$
3. If minor scheduling adjustments create a timeline gap, an automated fallback mechanism calculates the absolute difference and fetches the nearest chronological ELO row context, eliminating the risk of empty `NaN` entries.

---

## 4. Multi-Layer Data Governance & Export

The script implements an industry-standard database design pattern by isolating data into two distinct layers within your local `Data_Dynamic/` folder:

### 1. The Master Data Layer (`fixtureiq_dynamic_master.csv`)
This serves as your immutable source of truth. It stores the comprehensive dataset directly after the web scraping loop. It retains **all columns** natively returned by the SofaScore API—including the raw counts for duels, tackles, clearances, fouls, and intricate passing numbers. If you modify your machine learning objectives in the future, this file prevents the need to run time-consuming re-scraping tasks.

### 2. The Optimized Analytics Layer (`fixtureiq_dynamic_analytics_clean.csv`)
This file represents your feature-engineered modeling matrix, polished and optimized for machine learning algorithms.
* **Goalkeeper Filtration:** It filters out Goalkeepers (`position != 'G'`) to ensure outfield physical loading profiles are not skewed by low-intensity goalkeeper metrics.
* **Feature Selection:** Slices down columns strictly to high-density stressors (`acwr_ratio`, `min_last_7d`, `rest_days`), match context variables (`elo`, `rating`), and normalized player performance targets (`duel_success_pct`, `turnovers_per_90min`).

---

## 5. Execution Guide

To execute the pipeline, pass the targeted short-format season signature and output folder path into your terminal interface:

```bash
python fixtureiq_dynamic_pipeline.py --year "23/24" --output-dir "Data_Dynamic"