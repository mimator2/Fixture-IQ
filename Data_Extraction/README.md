# Data Extraction Pipelines

Three pipelines for building the Fixture IQ multi-competition dataset:

1. **API-Football extractor** (`extract_multi_competition_stats.py`) — primary data source
2. **FBref pipeline** (`football_data_pipeline.py`) — supplementary validation source
3. **SofaScore pipeline** (`sofascore_pipeline.py`) — additional match/player data

---

## API-Football Extractor

Extracts player-level and team-level match data across Premier League, FA Cup, League Cup, Champions League, and Community Shield for seasons 2022–2025.

### Setup

```bash
pip install requests pandas python-dotenv
```

Create `.env` with:
```bash
APIFOOTBALL_KEY=your_api_key_here
```

### Usage

```bash
python extract_multi_competition_stats.py
```

The script is force-mode by design: it ignores checkpoint files and `.SEASON_COMPLETE` markers, always rebuilding from the API. Before overwriting existing CSVs it creates timestamped backups.

Key design choices:
- Premier League teams are fetched **dynamically** from `/teams?league=39&season=<season>`
- FA Cup and Champions League fixtures are **filtered** to retain only those involving at least one Premier League team
- Team name aliases normalise inconsistencies across API endpoints
- Rate limiting: 0.25s delay between requests, 60s sleep on HTTP 429

### Outputs

Per-season directories under `Data/`:
- `API_SEASON_YYYY_YYYY/multi_competition_player_stats_*.csv`
- `API_SEASON_YYYY_YYYY/multi_competition_team_results_*.csv`
- Per-competition splits: `player_stats_premier_league_*.csv`, `player_stats_champions_league_*.csv`, etc.

---

## FBref Pipeline

A Selenium-based scraper for detailed FBref data (match logs, rosters, player stats, match reports). Useful for validation and supplementary context.

### Setup

```bash
pip install selenium beautifulsoup4 pandas webdriver-manager
```

Requires Chrome or Chromium installed.

### Usage

```bash
python football_data_pipeline.py \
  --squad-id 18bb7c10 \
  --team-slug Arsenal \
  --season 2023-2024 \
  --output-dir Data
```

Supports multiple teams, direct FBref URLs, shooting and roster data, and headless mode.

### Outputs

Per-team directories under `Data/`:
- `team_season_matches_all.csv`
- `by_competition/*.csv`
- `player_stats/*.csv`
- `match_reports/*/` (lineups, player stats, keeper stats per match)

---

## Data Flow

```
API-Football / FBref extraction
        ↓
  Data/API_SEASON_* / Data/SEASON_*
        ↓
  Data_Extraction/consolidation.py
        ↓
Data/Fixture_IQ_Data_Seasons_2022-2025.csv
        ↓
feature engineering → modelling → dashboard
```

The consolidated master CSV is the single input for `feature_engineering_v4b.py` and `export_data.py`.

---

## Notes

- The master CSV (`Fixture_IQ_Data_Seasons_2022-2025.csv`) is the authoritative modelling input.
- Re-running the API extractor does not require re-running the FBref pipeline, and vice versa.
- For detailed API-Football validation checks, rate-limit tuning, and troubleshooting, see inline comments in `extract_multi_competition_stats.py`.
