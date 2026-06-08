# Fixture IQ Data Extraction Pipelines

This folder contains the data extraction workflows used to build and enrich the Fixture IQ football analytics dataset.

Fixture IQ currently uses two complementary data extraction approaches:

1. **API-Football multi-competition extractor**

   * Main extractor for Fixture IQ modelling.
   * Extracts player-level and team-level match data across Premier League, FA Cup, League Cup, Champions League, and Community Shield.
   * Dynamically fetches Premier League teams from API-Football.
   * Filters FA Cup and Champions League fixtures to focus on Premier League-relevant matches.
   * Produces season-level CSV files used before feature engineering and modelling.

2. **FBref football data pipeline**

   * Web scraping pipeline for detailed team-level FBref data.
   * Extracts match logs, player stats, roster information, and detailed match reports.
   * Useful as a complementary source for validation, comparison, or additional team/player context.

The current Fixture IQ modelling workflow primarily depends on the **API-Football extractor**, while the FBref pipeline remains documented as an additional data source.

---

# Part I — API-Football Multi-Competition Extractor

## Overview

The main Fixture IQ extraction script is:

```bash
Data_Extraction/extract_multi_competition_stats.py
```

This script builds the raw multi-competition dataset used for downstream Fixture IQ feature engineering, CatBoost/XGBoost modelling, and dashboard development.

It extracts:

* player-level match statistics
* team-level match results
* Premier League fixtures
* domestic cup fixtures
* European fixtures involving Premier League teams
* Community Shield fixtures

The resulting CSV files are later used to create workload, congestion, recovery, injury-context, and performance-decline features.

---

## Pipeline Objective

The goal of the API-Football extractor is to create a consistent multi-season dataset that captures the competitive context around Premier League players.

Fixture IQ does not only need Premier League data. To study player workload, fatigue, and performance risk, the model must also account for matches played in:

* Premier League
* FA Cup
* League Cup
* Champions League
* Community Shield

This matters because a player’s future performance risk may be influenced by minutes and effort accumulated outside the league. For example, a Premier League match after a Champions League fixture may carry different fatigue or rotation risk than a league match after a full week of rest.

The API-Football extractor is therefore designed to produce the raw data foundation for:

```text
API-Football extraction
        ↓
season-level player/team CSV files
        ↓
feature engineering and enrichment
        ↓
Fixture_IQ_Data_Seasons_2022-2025.csv
        ↓
CatBoost / XGBoost modelling
        ↓
dashboard risk scores
```

---

## Features

✅ **Multi-season extraction** - Extracts API seasons `2022`, `2023`, and `2024`

✅ **Dynamic Premier League team discovery** - Fetches Premier League teams from API-Football instead of hard-coding them

✅ **Multi-competition support** - Extracts Premier League, FA Cup, League Cup, Champions League, and Community Shield data

✅ **FA Cup filtering** - Keeps only FA Cup fixtures involving at least one Premier League team

✅ **Champions League filtering** - Keeps only Champions League fixtures involving at least one Premier League team

✅ **Player-level statistics** - Produces one row per player per fixture

✅ **Team-level match results** - Produces two rows per fixture, one for each team

✅ **Force re-extraction mode** - Ignores old checkpoint files, season-complete markers, and existing fixture IDs

✅ **Backup before overwrite** - Existing CSVs are copied with timestamped backup names before replacement

✅ **Validation logs** - Checks that FA Cup and Champions League filtering worked correctly

✅ **Rate-limit handling** - Retries API requests and waits on HTTP `429` responses

✅ **Season-specific output folders** - Saves files into organized `API_SEASON_<season>` directories

✅ **Dashboard-ready foundation** - Produces the raw files used before Fixture IQ feature engineering and model training


---

## Competitions Extracted

| Competition          | API-Football League ID | Filtering Rule                                                 |
| -------------------- | ---------------------- | -------------------------------------------------------------- |
| **Premier League**   | `39`                   | Keep all fixtures                                              |
| **FA Cup**           | `45`                   | Keep fixtures where at least one team is a Premier League team |
| **League Cup**       | `48`                   | Keep all fixtures                                              |
| **Champions League** | `2`                    | Keep fixtures where at least one team is a Premier League team |
| **Community Shield** | `528`                  | Keep all fixtures                                              |

---

## Seasons Extracted

API-Football uses the **start year** of the football season as the `season` parameter.

| API Season | Football Season | Output Folder                |
| ---------: | --------------- | ---------------------------- |
|     `2022` | `2022-2023`     | `Data/API_SEASON_2022_2023/` |
|     `2023` | `2023-2024`     | `Data/API_SEASON_2023_2024/` |
|     `2024` | `2024-2025`     | `Data/API_SEASON_2024_2025/` |

The script is currently configured as:

```python
SEASONS = [2022, 2023, 2024]
```

This means the extractor rebuilds the three-season dataset covering:

```text
2022-2023
2023-2024
2024-2025
```

---

## API-Football Installation

### Prerequisites

* Python 3.8+
* API-Football API key
* pip
* Internet connection
* API-Football subscription with access to:

  * `/teams`
  * `/fixtures`
  * `/fixtures/players`

Install the required packages:

```bash
pip install requests pandas python-dotenv
```

The extractor uses:

| Package         | Purpose                              |
| --------------- | ------------------------------------ |
| `requests`      | API requests to API-Football         |
| `pandas`        | DataFrame creation and CSV export    |
| `python-dotenv` | Loading the API key from `.env`      |
| `pathlib`       | Path handling                        |
| `shutil`        | File backup before overwrite         |
| `datetime`      | Timestamped logging and backup names |

---

## API Key Setup

Create a `.env` file in the project or script directory with:

```bash
APIFOOTBALL_KEY=your_api_key_here
```

The script loads the key using:

```python
load_dotenv()
API_KEY = os.getenv("APIFOOTBALL_KEY")
```

If the key is missing, the script raises:

```text
APIFOOTBALL_KEY not found
```

---

## API-Football Usage

Run the extractor from the `Data_Extraction/` folder or from the project root:

```bash
python extract_multi_competition_stats.py
```

A correct run should print messages such as:

```text
FORCE RE-EXTRACTION: ALL TARGET SEASONS
API seasons: 2022, 2023, 2024
Football seasons: 2022-2023, 2023-2024, 2024-2025
Premier League teams are fetched dynamically from API-Football
FA Cup filter: keep only fixtures with at least one PL team
Champions League filter: keep only fixtures with at least one PL team
```

The script will process each season sequentially:

```text
STARTING SEASON 2022_2023
STARTING SEASON 2023_2024
STARTING SEASON 2024_2025
```

---

## Force Re-Extraction Behavior

This version is intentionally designed to rebuild the dataset from the API.

It ignores the older checkpoint-based skipping system, including:

```text
extraction_state_checkpoint.json
.SEASON_COMPLETE_2022_2023
.SEASON_COMPLETE_2023_2024
.SEASON_COMPLETE_2024_2025
existing fixture IDs
```

This is important because an older version of the extractor could skip a competition or season that had been marked as complete, even if the saved CSV was incomplete.

A correct run should **not** show:

```text
MARKED AS COMPLETE, SKIPPING
Already extracted, skipping
Total API Requests: 0
```

If you see those messages, you are probably running the old checkpoint-based script.

---

## Dynamic Premier League Team Fetching

The updated extractor no longer hard-codes Premier League teams by season.

Instead, for each API season it calls:

```text
/teams?league=39&season=<season>
```

Examples:

```text
/teams?league=39&season=2022
/teams?league=39&season=2023
/teams?league=39&season=2024
```

This returns the Premier League teams for that season.

The team list is cached during the run:

```python
PL_TEAMS_CACHE = {}
```

This prevents repeated API calls for the same season.

The dynamically fetched Premier League teams are then used to filter:

```text
FA Cup fixtures
Champions League fixtures
```

The core filtering rule is:

```python
home_team in pl_teams or away_team in pl_teams
```

This makes the pipeline more robust than manually defining season-specific team lists.

---

## Team Name Normalisation

The script includes a small alias dictionary:

```python
TEAM_NAME_ALIASES = {
    "Newcastle United": "Newcastle",
    "Wolverhampton Wanderers": "Wolves",
    "Wolverhampton": "Wolves",
    "Sheffield United": "Sheffield Utd",
    "Luton Town": "Luton",
    "Ipswich Town": "Ipswich",
    "West Ham United": "West Ham",
    "Leicester City": "Leicester",
    "Leeds United": "Leeds",
    "Southampton FC": "Southampton",
    "Manchester Utd": "Manchester United",
    "Man United": "Manchester United",
    "Man Utd": "Manchester United",
    "Man City": "Manchester City",
    "Tottenham Hotspur": "Tottenham",
    "Nottm Forest": "Nottingham Forest",
    "Nottingham Forest FC": "Nottingham Forest",
}
```

This does **not** hard-code which teams are eligible for a competition.

It only handles small naming differences between API responses. For example, one endpoint may return `Newcastle United`, while another may return `Newcastle`.

Without normalization, valid fixtures could be dropped due to inconsistent team names.

---

## API-Football Filtering Logic

### Premier League

All Premier League fixtures are kept.

```text
Premier League: keep all fixtures
```

This competition is also used to dynamically derive the season’s Premier League teams.

---

### FA Cup

The FA Cup contains teams from many divisions.

For Fixture IQ, only FA Cup fixtures where at least one team is a Premier League team are kept.

Filtering rule:

```python
home_team in pl_teams or away_team in pl_teams
```

Examples of retained FA Cup fixtures:

```text
Wigan vs Manchester United
Sunderland vs Newcastle
Bristol City vs West Ham
Coventry vs Manchester United
```

FA Cup matches where neither team is from the Premier League are removed.

This keeps the dataset focused on the same Premier League player population used later in the modelling workflow.

---

### League Cup

All League Cup fixtures are kept.

```text
League Cup: keep all fixtures
```

This was kept broad because League Cup fixtures are domestic and often include Premier League clubs, squad rotation, and workload-management signals.

---

### Champions League

Champions League fixtures are filtered dynamically.

The script keeps any Champions League fixture where either the home team or away team is part of that season’s dynamically fetched Premier League team set.

Filtering rule:

```python
home_team in pl_teams or away_team in pl_teams
```

This automatically keeps fixtures such as:

```text
Bayern Munich vs Arsenal
Real Madrid vs Manchester City
AC Milan vs Newcastle
```

and removes fixtures involving only non-English teams.

This logic fixes the previous 2023-2024 issue where only Manchester City’s Champions League campaign had been extracted. With dynamic filtering, the extractor should include all Champions League fixtures involving Premier League clubs present in the API response.

---

### Community Shield

All Community Shield fixtures are kept.

```text
Community Shield: keep all fixtures
```

Community Shield fixtures are useful because they can affect early-season workload, squad rhythm, and player minutes.

---

## API-Football Data Extracted

| Data Type                         | Description                                                                 | Output File                                   |
| --------------------------------- | --------------------------------------------------------------------------- | --------------------------------------------- |
| **Combined Player Stats**         | One row per player per fixture across all extracted competitions            | `multi_competition_player_stats_<season>.csv` |
| **Combined Team Results**         | Two rows per fixture, one from each team’s perspective                      | `multi_competition_team_results_<season>.csv` |
| **Premier League Player Stats**   | Player rows from Premier League fixtures                                    | `player_stats_premier_league_<season>.csv`    |
| **Premier League Team Results**   | Team rows from Premier League fixtures                                      | `team_results_premier_league_<season>.csv`    |
| **FA Cup Player Stats**           | Player rows from FA Cup fixtures involving at least one Premier League team | `player_stats_fa_cup_<season>.csv`            |
| **FA Cup Team Results**           | Team rows from filtered FA Cup fixtures                                     | `team_results_fa_cup_<season>.csv`            |
| **League Cup Player Stats**       | Player rows from League Cup fixtures                                        | `player_stats_league_cup_<season>.csv`        |
| **League Cup Team Results**       | Team rows from League Cup fixtures                                          | `team_results_league_cup_<season>.csv`        |
| **Champions League Player Stats** | Player rows from Champions League fixtures involving Premier League teams   | `player_stats_champions_league_<season>.csv`  |
| **Champions League Team Results** | Team rows from filtered Champions League fixtures                           | `team_results_champions_league_<season>.csv`  |
| **Community Shield Player Stats** | Player rows from Community Shield fixtures                                  | `player_stats_community_shield_<season>.csv`  |
| **Community Shield Team Results** | Team rows from Community Shield fixtures                                    | `team_results_community_shield_<season>.csv`  |

---

## API-Football Output Structure

After running the extractor, files are saved season by season:

```text
Data/
├── API_SEASON_2022_2023/
│   ├── multi_competition_player_stats_2022_2023.csv
│   ├── multi_competition_team_results_2022_2023.csv
│   ├── player_stats_premier_league_2022_2023.csv
│   ├── team_results_premier_league_2022_2023.csv
│   ├── player_stats_fa_cup_2022_2023.csv
│   ├── team_results_fa_cup_2022_2023.csv
│   ├── player_stats_league_cup_2022_2023.csv
│   ├── team_results_league_cup_2022_2023.csv
│   ├── player_stats_champions_league_2022_2023.csv
│   ├── team_results_champions_league_2022_2023.csv
│   ├── player_stats_community_shield_2022_2023.csv
│   └── team_results_community_shield_2022_2023.csv
│
├── API_SEASON_2023_2024/
│   ├── multi_competition_player_stats_2023_2024.csv
│   ├── multi_competition_team_results_2023_2024.csv
│   ├── player_stats_premier_league_2023_2024.csv
│   ├── team_results_premier_league_2023_2024.csv
│   ├── player_stats_fa_cup_2023_2024.csv
│   ├── team_results_fa_cup_2023_2024.csv
│   ├── player_stats_league_cup_2023_2024.csv
│   ├── team_results_league_cup_2023_2024.csv
│   ├── player_stats_champions_league_2023_2024.csv
│   ├── team_results_champions_league_2023_2024.csv
│   ├── player_stats_community_shield_2023_2024.csv
│   └── team_results_community_shield_2023_2024.csv
│
└── API_SEASON_2024_2025/
    ├── multi_competition_player_stats_2024_2025.csv
    ├── multi_competition_team_results_2024_2025.csv
    ├── player_stats_premier_league_2024_2025.csv
    ├── team_results_premier_league_2024_2025.csv
    ├── player_stats_fa_cup_2024_2025.csv
    ├── team_results_fa_cup_2024_2025.csv
    ├── player_stats_league_cup_2024_2025.csv
    ├── team_results_league_cup_2024_2025.csv
    ├── player_stats_champions_league_2024_2025.csv
    ├── team_results_champions_league_2024_2025.csv
    ├── player_stats_community_shield_2024_2025.csv
    └── team_results_community_shield_2024_2025.csv
```

---

## API-Football CSV File Descriptions

### `multi_competition_player_stats_<season>.csv`

This is the main player-level output.

Each row represents:

```text
one player in one fixture
```

Example columns:

| Column Group        | Example Columns                                                                  |
| ------------------- | -------------------------------------------------------------------------------- |
| Fixture context     | `fixture_id`, `date`, `competition`, `season`, `round`, `home_team`, `away_team` |
| Player identity     | `player_team`, `player_id`, `player_name`, `player_number`, `player_position`    |
| Match involvement   | `minutes_played`, `rating`, `is_captain`, `is_substitute`                        |
| Attacking stats     | `shots_total`, `shots_on_target`, `goals`, `assists`                             |
| Passing stats       | `passes_total`, `passes_key`, `passes_accuracy`                                  |
| Dribbling stats     | `dribbles_attempts`, `dribbles_success`                                          |
| Defensive stats     | `tackles_total`, `tackles_blocks`, `tackles_interceptions`                       |
| Duel and foul stats | `duels_total`, `duels_won`, `fouls_drawn`, `fouls_committed`                     |
| Discipline          | `cards_yellow`, `cards_red`                                                      |

---

### `multi_competition_team_results_<season>.csv`

This is the main team-level output.

Each fixture produces two rows:

```text
one row for the home team
one row for the away team
```

Example columns:

| Column Group    | Example Columns                                              |
| --------------- | ------------------------------------------------------------ |
| Fixture context | `fixture_id`, `date`, `competition`, `season`, `round`       |
| Team identity   | `team_name`, `team_id`, `is_home`, `opponent`, `opponent_id` |
| Match result    | `goals_for`, `goals_against`, `result`, `points`, `status`   |
| Team statistics | API-provided fixture statistics where available              |

This table is useful for merging team context into player-level records.

---

## API-Football Pipeline Phases

1. **Load API key**

   * Reads `APIFOOTBALL_KEY` from `.env`.

2. **Loop through seasons**

   * Processes API seasons `2022`, `2023`, and `2024`.

3. **Fetch Premier League teams dynamically**

   * Calls `/teams?league=39&season=<season>`.
   * Stores the team names in `PL_TEAMS_CACHE`.

4. **Loop through competitions**

   * Extracts Premier League, FA Cup, League Cup, Champions League, and Community Shield.

5. **Fetch fixtures**

   * Calls `/fixtures?league=<competition_id>&season=<season>`.

6. **Filter fixtures**

   * FA Cup: keep if at least one team is Premier League.
   * Champions League: keep if at least one team is Premier League.
   * Other competitions: keep all fixtures.

7. **Fetch fixture details**

   * Calls `/fixtures?id=<fixture_id>`.

8. **Fetch player statistics**

   * Calls `/fixtures/players?fixture=<fixture_id>`.

9. **Flatten player records**

   * Converts nested API player-stat structures into one row per player.

10. **Flatten team records**

* Converts each fixture into one row per team.

11. **Save season outputs**

* Saves combined and per-competition CSV files.

12. **Validate results**

* Checks FA Cup and Champions League filtering.

---

## API-Football Key Functions

| Function                                       | Purpose                                                                         |
| ---------------------------------------------- | ------------------------------------------------------------------------------- |
| `api_get()`                                    | Generic API-Football GET request with retries and rate-limit handling           |
| `get_all_fixtures()`                           | Fetches all fixtures for one competition and season                             |
| `get_fixture_info()`                           | Fetches detailed information for one fixture                                    |
| `get_player_statistics()`                      | Fetches player statistics for one fixture                                       |
| `get_pl_teams_for_season()`                    | Dynamically fetches Premier League teams for a given season                     |
| `get_pl_teams_cached()`                        | Caches Premier League teams to avoid repeated API calls                         |
| `filter_competition_fixtures()`                | Applies competition-specific filtering logic                                    |
| `diagnose_filtered_fixtures()`                 | Prints retained FA Cup and Champions League fixtures                            |
| `validate_champions_league_fixture_coverage()` | Reports which Premier League teams appear in retained Champions League fixtures |
| `extract_player_record()`                      | Converts nested player API data into a flat row                                 |
| `extract_team_records()`                       | Converts fixture data into home and away team result rows                       |
| `save_season_outputs()`                        | Saves combined and per-competition CSV outputs                                  |
| `validate_final_outputs()`                     | Runs final season-level validation checks                                       |

---

## API-Football Validation Checks

The script prints validation summaries after each season.

### FA Cup Validation

Expected message:

```text
✅ FA Cup validation passed: every retained FA Cup fixture has at least one PL team.
```

This confirms that every retained FA Cup fixture contains at least one Premier League team.

If invalid fixtures are found, the script prints them.

---

### Champions League Validation

Expected message:

```text
✅ Champions League validation passed: Premier League teams found dynamically.
```

The script also prints the Premier League teams found in Champions League player rows.

For example, the corrected 2023-2024 extraction should dynamically find teams such as:

```text
Arsenal
Manchester City
Manchester United
Newcastle
```

It will also include opponent teams in the player rows, such as:

```text
Bayern Munich
Real Madrid
Paris Saint Germain
AC Milan
```

This is expected because each retained Champions League fixture includes both teams’ player statistics.

---

## API-Football Backups and Overwrites

The script is force-mode by design.

Before overwriting an existing file, it creates a timestamped backup:

```text
player_stats_champions_league_2023_2024.csv.backup_YYYYMMDD_HHMMSS
```

This protects previous extractions while still allowing the data to be rebuilt.

Example:

```text
player_stats_champions_league_2023_2024.csv.backup_20260608_231831
```

---

## API-Football Rate Limiting and Retries

The script uses a delay between API calls:

```python
DELAY_BETWEEN_REQUESTS = 0.25
```

If API-Football returns HTTP `429`, the script waits before retrying:

```python
sleep_on_rate_limit = 60
```

If rate limits persist, increase the delay:

```python
DELAY_BETWEEN_REQUESTS = 0.5
```

or:

```python
DELAY_BETWEEN_REQUESTS = 1.0
```

---

## API-Football Important Notes

### 1. This script is force-mode

This version does not rely on the older checkpoint-based skipping system.

It ignores:

```text
extraction_state_checkpoint.json
.SEASON_COMPLETE markers
existing fixture IDs
```

This is intentional.

It prevents cases where a season or competition is skipped despite being incomplete.

---

### 2. Opponent rows in Champions League are expected

When a Champions League fixture involving a Premier League team is retained, the API returns player statistics for both teams.

For example:

```text
Real Madrid vs Manchester City
```

will include player rows for:

```text
Real Madrid
Manchester City
```

This is correct.

The filtering is done at the fixture level, not at the player-team level.

---

### 3. FA Cup opponent rows are expected

For the same reason, if a retained FA Cup fixture is:

```text
Wigan vs Manchester United
```

the player-level output may include rows for both:

```text
Wigan
Manchester United
```

This is correct because the fixture involves a Premier League team.

---

### 4. Dynamic team fetching is safer than hard-coding

The extractor derives Premier League teams from API-Football instead of manually listing teams.

This avoids mistakes across seasons and makes Champions League filtering more robust.

---

### 5. Team aliases are still useful

The alias dictionary is only used to normalize naming differences.

It is not used to decide who qualified for a competition.

---

## API-Football Troubleshooting

### Issue: `APIFOOTBALL_KEY not found`

Create a `.env` file containing:

```bash
APIFOOTBALL_KEY=your_api_key_here
```

Make sure it is located where `load_dotenv()` can find it.

---

### Issue: Fewer than 20 Premier League teams are fetched

The `/teams` endpoint should usually return 20 Premier League teams for a full season.

Possible causes:

1. API key or subscription issue.
2. API returned errors.
3. Temporary API response problem.
4. Team naming differences.

Check the logs for:

```text
Fetched X Premier League teams
```

---

### Issue: Too many FA Cup fixtures are kept

This usually means the Premier League team list could not be fetched, and the script kept all fixtures to avoid accidental data loss.

Look for this warning:

```text
Could not derive Premier League teams...
Keeping all fixtures...
```

---

### Issue: Champions League contains non-English teams

This is normal if those non-English teams played against a Premier League team.

Examples:

```text
Bayern Munich vs Arsenal
Real Madrid vs Manchester City
AC Milan vs Newcastle
```

The retained fixture includes both teams’ player stats.

---

### Issue: Champions League contains no Premier League teams

Check that the dynamic Premier League team list was fetched successfully for that season.

Look for:

```text
Fetched 20 Premier League teams
```

Then check the retained Champions League diagnostic table.

---

### Issue: The script still skips seasons

You are probably running the old checkpoint-based extractor.

A correct run should not print:

```text
MARKED AS COMPLETE, SKIPPING
Already extracted, skipping
Total API Requests: 0
```

Replace the old script with the updated force extractor and run again.

---

### Issue: Old incomplete Champions League data still appears in the modelling CSV

The extraction files may be corrected, but the consolidated modelling dataset may still be old.

After re-extracting the season files, rebuild:

```text
Fixture_IQ_Data_Seasons_2022-2025.csv
```

using the corrected season-level CSV files.

---

# Part II — FBref Football Data Pipeline

## Overview

The FBref pipeline is a separate Python web scraper and data pipeline for extracting detailed football match data from [FBref / Football Reference](https://fbref.com).

It automates data collection from FBref and organizes it into structured CSV files for analysis.

This pipeline is useful when the project needs:

* detailed FBref match logs
* roster data
* team-specific player statistics
* per-match report tables
* complementary validation against API-Football

The FBref pipeline is not the same as the API-Football extractor. It uses browser automation and HTML parsing rather than API requests.

---

## FBref Features

✅ **Multi-team support** - Extract data for one or multiple teams in a single run
✅ **Comprehensive data extraction** - Match logs, player stats, rosters, and detailed per-match reports
✅ **Flexible input methods** - Use team IDs, team slugs, or direct FBref URLs
✅ **Organized output** - Automatic directory structure with data split by competition
✅ **Robust HTML parsing** - Fallback mechanisms if FBref changes table structures
✅ **Headless mode** - Run silently in background without displaying browser
✅ **Dynamic content handling** - JavaScript rendering support for fully-loaded pages

---

## FBref Data Extracted

| Data Type              | Description                                   | Output File            |
| ---------------------- | --------------------------------------------- | ---------------------- |
| **Match Logs**         | All matches with results, opponents, venues   | `matches_all.csv`      |
| **Competition Splits** | Matches organized by competition              | `by_competition/*.csv` |
| **Opponents**          | Unique list of all opponents faced            | `opponents.csv`        |
| **Team Metadata**      | Teams with stadium information                | `teams.csv`            |
| **Player Roster**      | Squad roster with player details              | `roster.csv`           |
| **Player Stats**       | Standard player statistics per competition    | `player_stats/*.csv`   |
| **Match Reports**      | Per-match lineups, player stats, keeper stats | `match_reports/*/`     |

---

## FBref Installation

### Prerequisites

* Python 3.8+
* Google Chrome or Chromium browser installed
* pip

Install the required packages:

```bash
pip install selenium beautifulsoup4 pandas webdriver-manager
```

These packages provide:

* **selenium** - Web browser automation
* **beautifulsoup4** - HTML parsing
* **pandas** - Data manipulation and CSV export
* **webdriver-manager** - Automatic Chrome driver management

---

## FBref Usage

### Finding Team Information

Before running the FBref script, you need:

1. **Squad ID** - Unique FBref identifier for the team
2. **Team Slug** - Team name as it appears in URLs
3. **Season** - Season identifier, for example `2023-2024`

Where to find this information:

1. Go to [fbref.com](https://fbref.com)
2. Find your team’s stats page
3. The URL will look like:

```text
https://fbref.com/en/squads/18bb7c10/2023-2024/Arsenal-Stats
```

Extract:

```text
squad_id = 18bb7c10
season = 2023-2024
team_slug = Arsenal
```

---

## FBref Mode 1: Single Team

Extract data for one team using squad ID and team slug:

```bash
python football_data_pipeline.py \
  --squad-id 18bb7c10 \
  --team-slug Arsenal \
  --season 2023-2024 \
  --output-dir Data
```

---

## FBref Mode 2: Multiple Teams Manually

Extract data for multiple teams using comma/colon-separated format:

```bash
python football_data_pipeline.py \
  --team "18bb7c10:Arsenal" \
  --team "5bfb051f:Brighton" \
  --team "ba4914d6:Manchester-City" \
  --season 2023-2024 \
  --output-dir Data
```

Format:

```text
<squad_id>:<team_slug>
```

or:

```text
<squad_id>,<team_slug>
```

---

## FBref Mode 3: From FBref URLs

Extract team information automatically from FBref URLs:

```bash
python football_data_pipeline.py \
  --team-url "https://fbref.com/en/squads/18bb7c10/2023-2024/Arsenal-Stats" \
  --season 2023-2024 \
  --output-dir Data
```

Multiple teams:

```bash
python football_data_pipeline.py \
  --team-url "https://fbref.com/en/squads/18bb7c10/2023-2024/Arsenal-Stats" \
  --team-url "https://fbref.com/en/squads/ba4914d6/2023-2024/Manchester-City-Stats" \
  --season 2023-2024 \
  --output-dir Data
```

---

## FBref Mode 4: With Optional Data Sources

Include shooting stats and roster data:

```bash
python football_data_pipeline.py \
  --squad-id 18bb7c10 \
  --team-slug Arsenal \
  --season 2023-2024 \
  --shooting-url "https://fbref.com/en/squads/18bb7c10/2023-2024/Arsenal-Match-Logs-Shooting" \
  --roster-url "https://fbref.com/en/squads/18bb7c10/2023-2024/roster/Arsenal-Roster-Details" \
  --headless \
  --output-dir Data
```

---

## FBref Mode 5: Headless Mode

Run the script without displaying the browser window:

```bash
python football_data_pipeline.py \
  --squad-id 18bb7c10 \
  --team-slug Arsenal \
  --season 2023-2024 \
  --headless \
  --output-dir Data
```

---

## FBref Help Command

View all available options:

```bash
python football_data_pipeline.py --help
```

---

## FBref Output Structure

After running the FBref script, the output looks like:

```text
Data/
└── manchester_city_2023_2024/
    ├── manchester_city_2023_2024_matches_all.csv
    ├── manchester_city_2023_2024_opponents.csv
    ├── manchester_city_2023_2024_teams.csv
    ├── manchester_city_2023_2024_roster.csv
    │
    ├── by_competition/
    │   ├── manchester_city_2023_2024_premier_league.csv
    │   ├── manchester_city_2023_2024_champions_lg.csv
    │   ├── manchester_city_2023_2024_fa_cup.csv
    │   ├── manchester_city_2023_2024_efl_cup.csv
    │   ├── manchester_city_2023_2024_community_shield.csv
    │   └── manchester_city_2023_2024_super_cup.csv
    │
    ├── player_stats/
    │   ├── manchester_city_2023_2024_players_all_competitions.csv
    │   ├── manchester_city_2023_2024_players_premier_league.csv
    │   └── manchester_city_2023_2024_players_fa_cup.csv
    │
    └── match_reports/
        ├── 2023-08-06_community_shield_arsenal/
        │   ├── 2023-08-06_community_shield_arsenal_lineups.csv
        │   ├── 2023-08-06_community_shield_arsenal_player_stats.csv
        │   └── 2023-08-06_community_shield_arsenal_goalkeeper_stats.csv
        ├── 2023-08-11_premier_league_burnley/
        │   ├── lineups.csv
        │   ├── player_stats.csv
        │   └── goalkeeper_stats.csv
        └── ... one folder per match
```

---

## FBref CSV File Descriptions

### `matches_all.csv`

| Column             | Description                   |
| ------------------ | ----------------------------- |
| `Date`             | Match date                    |
| `Day`              | Day of week                   |
| `Venue`            | Home/Away                     |
| `Result`           | Match result, W/D/L           |
| `GF`               | Goals For                     |
| `GA`               | Goals Against                 |
| `Opponent`         | Opponent name                 |
| `Competition`      | Competition type              |
| `Round`            | Round or week number          |
| `Match_Report_URL` | Link to detailed match report |

---

### `roster.csv`

| Column     | Description             |
| ---------- | ----------------------- |
| `Player`   | Player name             |
| `Age`      | Player age              |
| `Country`  | Nationality             |
| `Position` | Playing position        |
| `DL_MP`    | Domestic League matches |
| `DL_Min`   | Domestic League minutes |
| `DL_Gls`   | Domestic League goals   |

---

### `player_stats/*.csv`

Contains detailed player statistics per player per competition, including goals, assists, minutes, and other FBref-provided values.

---

### `match_reports/*/lineups.csv`

| Column           | Description                  |
| ---------------- | ---------------------------- |
| `Player`         | Player name                  |
| `Jersey_Number`  | Shirt number                 |
| `Lineup_Section` | Starter or bench             |
| `Formation`      | Formation used, e.g. `4-3-3` |

---

## FBref Command-Line Arguments

```text
usage: football_data_pipeline.py [-h] [--squad-id SQUAD_ID] --season SEASON
                                 [--team-slug TEAM_SLUG] [--team TEAM]
                                 [--team-url TEAM_URL] [--output-dir OUTPUT_DIR]
                                 [--shooting-url SHOOTING_URL]
                                 [--roster-url ROSTER_URL] [--headless]
```

| Argument                  | Description                                             |
| ------------------------- | ------------------------------------------------------- |
| `-h`, `--help`            | Show help message and exit                              |
| `--squad-id SQUAD_ID`     | FBref squad ID, e.g. `18bb7c10`                         |
| `--season SEASON`         | Season, e.g. `2023-2024`                                |
| `--team-slug TEAM_SLUG`   | Team slug for URLs, e.g. `Arsenal`                      |
| `--team TEAM`             | Multi-team format: `<squad_id>:<team_slug>`, repeatable |
| `--team-url TEAM_URL`     | FBref team stats URL, repeatable                        |
| `--output-dir OUTPUT_DIR` | Output directory, default: `Data`                       |
| `--shooting-url URL`      | Optional direct shooting stats URL                      |
| `--roster-url URL`        | Optional direct roster URL                              |
| `--headless`              | Run Chrome in headless mode                             |

---

## FBref Pipeline Phases

1. **URL Loading**

   * Opens FBref pages with Selenium WebDriver.
   * Scrolls page to trigger JavaScript rendering.
   * Waits for dynamic content to load.

2. **HTML Parsing**

   * BeautifulSoup extracts data from HTML.
   * Looks for match log tables by ID or content matching.
   * Uses fallback mechanisms if FBref changes structure.

3. **Data Normalization**

   * Maps FBref column codes to readable names.
   * Example: `gf` becomes `GF`, `opponent` becomes `Opponent`.

4. **CSV Export**

   * Saves data to organized directory structure.
   * Main tables go to root.
   * Competitions are split into subfolders.
   * Match reports get individual folders.

---

## FBref Key Functions

| Function                          | Purpose                                             |
| --------------------------------- | --------------------------------------------------- |
| `_load_html()`                    | Selenium-based page loading with JavaScript support |
| `_extract_table_rows()`           | Parse match log tables with fallback detection      |
| `_extract_roster_rows()`          | Extract player roster data                          |
| `_extract_standard_stats_table()` | Parse player statistics tables                      |
| `_save_match_report_tables()`     | Download and save per-match detail data             |
| `parse_team_from_stats_url()`     | Extract `squad_id` and `team_slug` from URLs        |
| `sanitize_filename()`             | Create filesystem-safe filenames                    |

---

## FBref Important Notes

### Performance

Approximate runtime:

| Mode           | Runtime                                                            |
| -------------- | ------------------------------------------------------------------ |
| Single team    | 5-10 minutes                                                       |
| Multiple teams | 30-60+ minutes                                                     |
| Match reports  | Longest phase, because each match requires an individual page load |

---

### Rate Limiting

FBref may block excessive requests.

If needed, add delays between requests:

```python
time.sleep(2)
```

Use `--headless` to run the browser in the background.

---

### Dynamic Content

The script waits for dynamic page rendering.

Some data may not load if FBref changes its JavaScript or table structure.

Check console output for warnings about missing tables.

---

### Browser Requirements

The FBref pipeline requires:

* Chrome or Chromium installed
* compatible ChromeDriver
* `webdriver-manager` to automatically download the correct driver

It should work on:

* Linux
* macOS
* Windows

---

## FBref Troubleshooting

### Issue: `No suitable match log table found`

Possible cause:

```text
FBref changed table structure
```

Solution:

* Check whether the table still exists on the FBref website.
* Update the table detection logic if needed.

---

### Issue: Chrome driver not found

Possible cause:

```text
Chrome or Chromium is not installed
```

Solution:

* Install Chrome from Google Chrome’s website.
* Re-run the script.
* `webdriver-manager` should download the correct driver.

---

### Issue: Season mismatch

Possible cause:

```text
URL season does not match --season argument
```

Solution:

Make sure both use the same season format:

```text
2023-2024
```

---

### Issue: Empty CSV files

Possible causes:

1. No data extracted from page.
2. FBref table structure changed.
3. FBref does not have data for that team/season.
4. Dynamic content did not load.

Solutions:

* Verify FBref still has the data.
* Run without headless mode to see browser behavior.
* Check console warnings.
* Update HTML parsing logic if needed.

---

### Issue: Too many false timeouts

Possible cause:

```text
Slow internet connection
```

Solution:

Increase timeout in the code:

```python
driver.set_page_load_timeout(60)
```

---

## Data Quality Notes

### API-Football Data Quality Notes

1. **Player statistics depend on API availability**

   * Some fixtures may return no player statistics.
   * The script logs a warning and continues.

2. **Opponent rows are expected**

   * Retained fixtures include both teams.
   * This is correct for Champions League and FA Cup.

3. **Team names may differ across endpoints**

   * The alias dictionary reduces mismatches.
   * If new naming differences appear, add them to `TEAM_NAME_ALIASES`.

4. **Rebuild consolidated data after extraction**

   * The modelling dataset must be rebuilt after correcting raw files.

---

### FBref Data Quality Notes

1. **Player stats are not always available**

   * Some FBref pages do not have `stats_standard` tables.
   * The script prints a warning but continues.

2. **Match report variations**

   * Not all matches have complete lineups, stats, or goalkeeper tables.
   * Some older matches may have incomplete data.

3. **Opponent names**

   * Stadium/location fields may be incomplete.
   * Some fields may be filled with `"Unknown"`.

4. **International cups**

   * Some international or cup competition data may be limited.

---

## Recommended Data Validation

After extraction, check:

```text
Number of fixtures by competition
Number of player rows by competition
Number of team rows by competition
Premier League teams found dynamically
FA Cup retained fixtures
Champions League retained fixtures
Duplicate fixture IDs
Missing player IDs
Missing dates
Invalid or null ratings
```

For the modelling dataset, also check:

```text
Date range
Season labels
Player-team consistency
Competition labels
Missing values
Rolling feature availability
Target distribution
Train/test season split
```

---

## Recommended Git Workflow

After updating the extraction code and README locally:

```bash
cd /home/vant/Documentos/FOOTBALL_ANALYTICS/MASTER/PROYECT/Fixture-IQ

git checkout xgboost-miquel
git pull origin xgboost-miquel

mkdir -p Data_Extraction

cp /home/vant/Documentos/FOOTBALL_ANALYTICS/MASTER/PROYECT/Data_Extraction/extract_multi_competition_stats.py \
   Data_Extraction/extract_multi_competition_stats.py

cp /home/vant/Documentos/FOOTBALL_ANALYTICS/MASTER/PROYECT/Data_Extraction/README.md \
   Data_Extraction/README.md

git status

git add Data_Extraction/extract_multi_competition_stats.py Data_Extraction/README.md

git commit -m "Update data extraction pipelines and documentation"

git push origin xgboost-miquel
```

---

## Current Status

The API-Football extractor has been updated to solve the previous 2023-2024 Champions League issue where only Manchester City’s campaign had been saved.

The new version dynamically derives Premier League teams from API-Football and filters Champions League fixtures by checking whether either team belongs to the Premier League for that season.

This should correctly include Champions League fixtures involving Premier League clubs such as:

```text
Arsenal
Manchester City
Manchester United
Newcastle
```

for the 2023-2024 season, while automatically excluding Champions League fixtures involving only non-English teams.

The updated extractor also ensures FA Cup data is focused on fixtures involving Premier League clubs, making the dataset more aligned with the Fixture IQ modelling population.

The FBref pipeline remains available as a complementary data source for detailed match logs, rosters, player stats, and match reports.


