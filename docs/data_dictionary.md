# Data Sources & Documentation

## 📊 Data Architecture

**Fixture IQ** uses a multi-source integration strategy to build a comprehensive dataset linking fixture congestion with team performance and squad management.

---

## 🔗 Primary Data Sources

### 1. Match Calendar Data

**Source**: Premier League & UEFA Official Records  
**Content**: Complete fixture schedule for 2024-2025 season  
**Granularity**: Match-level (date, teams, competition, venue)

**Competitions Included**:
- Premier League (domestic league)
- UEFA Champions League (European club competition)
- FA Cup (domestic knockout)
- EFL Cup (League Cup - domestic knockout)
- Community Shield (pre-season friendly)

**Data Points Collected**:
- Match date and time
- Home and away teams
- Competition type
- Match outcome (goals for, goals against)
- Final result (win/draw/loss)

**Processing**: 
- Standardized date formats (YYYY-MM-DD)
- Unified team naming across sources
- Chronologically sorted by team and match date

---

### 2. Performance Metrics

**Source**: Public Football Statistics Databases (FBRef, Opta Sports Data)  
**Content**: Team-level performance indicators  
**Granularity**: Match-level and aggregated

**Metrics Available**:
- Points (3 for win, 1 for draw, 0 for loss)
- Goals for and against
- Goal difference
- Points per match (PPM)
- Expected goals (xG) - when available
- Win/draw/loss records by competition

**Coverage**: 
- All matches in each competition
- Aggregated by team and competition type
- Temporal trends across season

---

### 3. Squad & Roster Data

**Source**: Transfermarkt, Official Club Records  
**Content**: Squad composition and player availability  
**Optional/Future Enhancement**: Injury lists, suspension records, transfer dates

**Use Case**: 
- Context for squad rotation analysis
- Identification of forced vs. tactical changes
- Player availability constraints

---

### 4. Fixture Sequence Context

**Source**: Derived from match schedule (SofaScore & FBref)  
**Content**: Calculated relationships between consecutive matches  

**Computed Indicators**:
- **Days since previous match**: Rest period between fixtures
- **Matches in rolling 7-day window**: Density of fixtures in one week
- **Matches in rolling 14-day window**: Density of fixtures in two weeks
- **Cumulative matches**: Season load running total
- **Rest category**: `well_rested` (>6 d), `normal` (4–6 d), `congested` (≤3 d), `season_opener`
- **Away leg sequence** *(new)*: Consecutive running count of consecutive away fixtures; resets to 0 on a home match (proxy for travel burden)
- **Home-away alternation rate** *(new)*: Rolling 5-match fraction of H↔A switches (proxy for scheduling/travel stress)

---

## 📂 Data Files in This Repository

### Dataset Files

Location: `/data/` (gitignored; downloaded by the extraction pipelines)

Extraction methods:
| Script | Source | Status |
|--------|--------|--------|
| `football_data_pipeline.py` | FBref (Selenium) | ✅ Canonical |
| `fbref_advanced_pipeline.py` | FBref (Selenium + 8-table merger) | ✅ Active |
| `sofascore_direct.py` | SofaScore (direct API + Playwright bypass) | ✅ Canonical (replaces legacy ScraperFC scripts) |
| `data_extraction/football_data_pipeline.py` | Fixture-IQ fork (cloudscraper + undetected-chromedriver) | ❌ Removed — use root `football_data_pipeline.py` |

Data files are organised per-team per-season by each pipeline under the `Data/` (gitignored) directory:
- `Data/champions_league_{Y}_{Y+1}/` — SofaScore UCL data
- `Data/premier_league_{Y}_{Y+1}/` — SofaScore EPL data
- `{team_slug}_{season}/` — FBref per-team data (match logs, rosters, match reports)

Canonical column names used across extracted files:
| Column | Description |
|--------|-------------|
| `date` / `Date` | Match date (UTC) |
| `team` | Team name |
| `opponent` | Opposing team |
| `competition` | League, UCL, FA Cup, EFL Cup … |
| `venue` | Home / Away |
| `gf`, `ga` | Goals for / Goals against |
| `result` | Win / Draw / Loss |
| `days_since_last_match` | Days since previous fixture |
| `away_leg_sequence` | Consecutive running count of away fixtures |
| `home_away_alternation_rate` | Rolling(5) fraction of H↔A switches |
---

### Master Dataset (Generated)

**Created By**: `01_Match_Calendar_and_Workload_Analysis.ipynb`  
**Purpose**: Unified dataset with all calculated metrics

**Enhanced Columns** (beyond source data):
- `competition_category`: Standardized competition grouping
- `days_since_previous_match`: Recovery days between fixtures
- `matches_last_7_days`: Rolling count of matches
- `matches_last_14_days`: Fixture density indicator
- `matches_last_21_days`: Extended scheduling pressure
- `congestion_category`: Low/Medium/High classification
- `before_europe`: Boolean flag (match precedes European fixture)
- `after_europe`: Boolean flag (match follows European fixture)
- `rolling_points_5`: 5-match rolling average of points
- `rolling_gd_5`: 5-match rolling average of goal difference

**Analytical Scopes**:
- **Scope A** (~220 records): All competitions (fixture burden analysis)
- **Scope B** (~152 records): Premier League only (competitive fairness)
- **Scope C** (subset of B): European context (hangover effects)

---

## 🎨 Visual Assets

Location: `/EDA/LOGOS/`

**Competition Logos**:
- `england_english-premier-league_128x128.football-logos.cc.png` - Premier League
- `tournaments_uefa-champions-league_128x128.football-logos.cc.png` - Champions League
- `england_emirates-fa-cup_128x128.football-logos.cc.png` - FA Cup
- `england_efl-cup_128x128.football-logos.cc.png` - EFL Cup
- `england_fa-community-shield_128x128.football-logos.cc.png` - Community Shield

**Format**: PNG, 128×128 pixels, transparent background  
**Source**: football-logos.cc (public domain)  
**Usage**: Embedded in visualizations for competition context

---

## 📊 Output Visualizations

Location: `/EDA/VISUALIZATIONS/`

Generated figures include:
- **Team workload by competition** (grouped bar chart with logos)
- **Weekly fixture density heatmap** (calendar view)
- **Rolling congestion vs. performance** (time-series trends)
- **Team-specific load analysis** (individual resilience profiles)
- **Competition transition matrix** (fixture sequence impact)

**Format**: PNG, 300 DPI  
**Purpose**: Analysis documentation and stakeholder communication

---

## 🔄 Data Integration Workflow

```
Official Match Records
    ↓
CSV File Import (Pandas)
    ↓
Data Cleaning & Standardization
    ↓
Rest Period Calculation
    ↓
Congestion Indicator Computation
    ↓
Competition Context Flagging
    ↓
Master Dataset Creation
    ↓
Statistical Analysis & Visualization
    ↓
Performance Insights & Recommendations
```

---

## 🔐 Data Governance

### Data Accuracy
- Source verification against official records
- Cross-reference between multiple sources when available
- Duplicate detection and removal
- Missing value validation

### Data Completeness
- All required fields present
- No silent NULL values
- Explicit handling of edge cases (e.g., abandoned matches, postponements)

### Data Currency
- Updated as matches are completed during season
- Historical data from 2024-2025 season finalized post-May 2025

---

## 🚀 Data Collection for Future Seasons

To extend this project beyond 2024-25, collect:

1. **Match Data**: Official fixture lists and results
2. **Performance Metrics**: Team statistics and advanced analytics (xG, progressive actions)
3. **Lineup Data**: Starting XI and squad rotation patterns
4. **Injury/Suspension Data**: Squad availability constraints
5. **Travel Context**: International match days, geographical distance

---

## 📝 Data Documentation Standards

Each CSV file includes:
- **Header row**: Column names clearly labeled
- **Data types**: Inferred but documented (string, integer, date)
- **Missing values**: Explicitly marked or excluded with documentation
- **Value ranges**: Known constraints (e.g., Points ∈ {0, 1, 3})

---

## 🔗 References

- **Premier League**: Official website (premierleague.com)
- **UEFA Champions League**: Official records (uefa.com)
- **Football Statistics**: FBRef, Opta Sports, TransferMarkt
- **Logo Source**: football-logos.cc

---

## 📧 Data Questions

For questions about specific data fields, collection methods, or accuracy, please review the notebook documentation in `01_Match_Calendar_and_Workload_Analysis.ipynb` or open an issue.

---

**Last Updated**: May 2026  
**Data Period**: August 2024 - May 2025  
**Version**: 1.0
