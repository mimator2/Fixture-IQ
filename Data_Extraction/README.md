# FBref Football Data Pipeline

A comprehensive Python web scraper and data pipeline for extracting detailed football (soccer) match data from [FBref (Football Reference)](https://fbref.com). This tool automates data collection from FBref and organizes it into well-structured CSV files for analysis.

## 📋 Features

✅ **Multi-team support** - Extract data for one or multiple teams in a single run  
✅ **Comprehensive data extraction** - Match logs, player stats, rosters, and detailed per-match reports  
✅ **Flexible input methods** - Use team IDs, team slugs, or direct FBref URLs  
✅ **Organized output** - Automatic directory structure with data split by competition  
✅ **Robust HTML parsing** - Fallback mechanisms if FBref changes table structures  
✅ **Headless mode** - Run silently in background without displaying browser  
✅ **Dynamic content handling** - JavaScript rendering support for fully-loaded pages  

## 📊 Data Extracted

| Data Type | Description | Output File |
|-----------|-------------|-------------|
| **Match Logs** | All matches with results, opponents, venues | `matches_all.csv` |
| **Competition Splits** | Matches organized by competition | `by_competition/*.csv` |
| **Opponents** | Unique list of all opponents faced | `opponents.csv` |
| **Team Metadata** | Teams with stadium information | `teams.csv` |
| **Player Roster** | Squad roster with player details | `roster.csv` |
| **Player Stats** | Standard player statistics per competition | `player_stats/*.csv` |
| **Match Reports** | Per-match lineups, player stats, keeper stats | `match_reports/*/` |

## 🚀 Installation

### Prerequisites

- Python 3.8+
- Google Chrome or Chromium browser installed
- pip (Python package manager)

These packages provide:
- **selenium** - Web browser automation
- **beautifulsoup4** - HTML parsing
- **pandas** - Data manipulation and CSV export
- **webdriver-manager** - Automatic Chrome driver management

## 🎯 Usage

### Finding Team Information

Before running the script, you'll need:
1. **Squad ID** - Unique FBref identifier for the team
2. **Team Slug** - Team name as it appears in URLs
3. **Season** - Season identifier (e.g., `2023-2024`)

**Where to find this info:**
- Go to [fbref.com](https://fbref.com)
- Find your team's stats page
- The URL will look like: `https://fbref.com/en/squads/18bb7c10/2023-2024/Arsenal-Stats`
- Extract: `squad_id=18bb7c10`, `season=2023-2024`, `team_slug=Arsenal`

### Mode 1: Single Team (Simplest)

Extract data for one team using squad ID and team slug:

```bash
python football_data_pipeline.py \
  --squad-id 18bb7c10 \
  --team-slug Arsenal \
  --season 2023-2024 \
  --output-dir Data
```

### Mode 2: Multiple Teams (Manual)

Extract data for multiple teams using comma/colon-separated format:

```bash
python football_data_pipeline.py \
  --team "18bb7c10:Arsenal" \
  --team "5bfb051f:Brighton" \
  --team "ba4914d6:Manchester-City" \
  --season 2023-2024 \
  --output-dir Data
```

Format: `<squad_id>:<team_slug>` or `<squad_id>,<team_slug>`

### Mode 3: From FBref URLs (Easiest)

Extract team info automatically from FBref URLs:

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

### Mode 4: With Optional Data Sources

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

### Mode 5: Headless Mode (Background Execution)

Run the script without displaying the browser window:

```bash
python football_data_pipeline.py \
  --squad-id 18bb7c10 \
  --team-slug Arsenal \
  --season 2023-2024 \
  --headless \
  --output-dir Data
```

### Help Command

View all available options:

```bash
python football_data_pipeline.py --help
```

## 📁 Output Structure

After running the script, you'll get this directory structure:

```
Data/
└── manchester_city_2023_2024/
    ├── manchester_city_2023_2024_matches_all.csv      # All 57 matches
    ├── manchester_city_2023_2024_opponents.csv        # 26 opponents
    ├── manchester_city_2023_2024_teams.csv            # Teams metadata
    ├── manchester_city_2023_2024_roster.csv           # Squad roster (if roster_url provided)
    │
    ├── by_competition/                                 # Matches split by competition
    │   ├── manchester_city_2023_2024_premier_league.csv
    │   ├── manchester_city_2023_2024_champions_lg.csv
    │   ├── manchester_city_2023_2024_fa_cup.csv
    │   ├── manchester_city_2023_2024_efl_cup.csv
    │   ├── manchester_city_2023_2024_community_shield.csv
    │   └── manchester_city_2023_2024_super_cup.csv
    │
    ├── player_stats/                                   # Player statistics per competition
    │   ├── manchester_city_2023_2024_players_all_competitions.csv
    │   ├── manchester_city_2023_2024_players_premier_league.csv
    │   └── manchester_city_2023_2024_players_fa_cup.csv
    │
    └── match_reports/                                  # Detailed per-match data
        ├── 2023-08-06_community_shield_arsenal/
        │   ├── 2023-08-06_community_shield_arsenal_lineups.csv
        │   ├── 2023-08-06_community_shield_arsenal_player_stats.csv
        │   └── 2023-08-06_community_shield_arsenal_goalkeeper_stats.csv
        ├── 2023-08-11_premier_league_burnley/
        │   ├── lineups.csv
        │   ├── player_stats.csv
        │   └── goalkeeper_stats.csv
        └── ... (one folder per match)
```

## 📝 CSV File Descriptions

### matches_all.csv
| Column | Description |
|--------|-------------|
| Date | Match date |
| Day | Day of week |
| Venue | Home/Away |
| Result | Match result (W/D/L) |
| GF | Goals For |
| GA | Goals Against |
| Opponent | Opponent name |
| Competition | Competition type |
| Round | Round/Week number |
| Match_Report_URL | Link to detailed match report |

### roster.csv
| Column | Description |
|--------|-------------|
| Player | Player name |
| Age | Player age |
| Country | Nationality |
| Position | Playing position |
| DL_MP | Domestic League matches |
| DL_Min | Domestic League minutes |
| DL_Gls | Domestic League goals |

### player_stats/*.csv
Contains detailed statistics per player per competition (goals, assists, minutes, etc.)

### match_reports/*/lineups.csv
| Column | Description |
|--------|-------------|
| Player | Player name |
| Jersey_Number | Shirt number |
| Lineup_Section | Starter/Bench |
| Formation | Formation used (e.g., 4-3-3) |

## 💡 Usage Examples

### Example 1: Extract Premier League Team Data
```bash
python football_data_pipeline.py \
  --squad-id 18bb7c10 \
  --team-slug Arsenal \
  --season 2023-2024 \
  --output-dir Data
```

### Example 2: Compare Multiple Teams
```bash
python football_data_pipeline.py \
  --team "18bb7c10:Arsenal" \
  --team "ba4914d6:Manchester-City" \
  --team "5bfb051f:Brighton" \
  --season 2023-2024 \
  --output-dir Data \
  --headless
```

### Example 3: Run from Multiple URLs
```bash
python football_data_pipeline.py \
  --team-url "https://fbref.com/en/squads/18bb7c10/2023-2024/Arsenal-Stats" \
  --team-url "https://fbref.com/en/squads/ba4914d6/2023-2024/Manchester-City-Stats" \
  --season 2023-2024 \
  --output-dir Data
```

### Example 4: Complete Data with All Options
```bash
python football_data_pipeline.py \
  --squad-id 18bb7c10 \
  --team-slug Arsenal \
  --season 2023-2024 \
  --shooting-url "https://fbref.com/en/squads/18bb7c10/2023-2024/Arsenal-Match-Logs-Shooting" \
  --roster-url "https://fbref.com/en/squads/18bb7c10/2023-2024/roster/Arsenal-Roster-Details" \
  --output-dir Data \
  --headless
```

## ⚙️ Command-Line Arguments

```
usage: football_data_pipeline.py [-h] [--squad-id SQUAD_ID] --season SEASON 
                                 [--team-slug TEAM_SLUG] [--team TEAM] 
                                 [--team-url TEAM_URL] [--output-dir OUTPUT_DIR] 
                                 [--shooting-url SHOOTING_URL] 
                                 [--roster-url ROSTER_URL] [--headless]

Optional arguments:
  -h, --help              Show this help message and exit
  --squad-id SQUAD_ID     FBref squad ID (e.g., 18bb7c10)
  --season SEASON         Season (e.g., 2023-2024) [REQUIRED]
  --team-slug TEAM_SLUG   Team slug for URLs (e.g., Arsenal)
  --team TEAM             Multi-team format: '<squad_id>:<team_slug>' (repeatable)
  --team-url TEAM_URL     FBref team stats URL (repeatable)
  --output-dir OUTPUT_DIR Output directory (default: Data)
  --shooting-url URL      Optional direct shooting stats URL
  --roster-url URL        Optional direct roster URL
  --headless              Run Chrome in headless mode (no visible window)
```

## 🔧 How It Works

### Pipeline Phases

1. **URL Loading** - Opens FBref pages with Selenium WebDriver
   - Scrolls page to trigger JavaScript rendering
   - Waits 8 seconds for dynamic content to load

2. **HTML Parsing** - BeautifulSoup extracts data from HTML
   - Looks for match log tables by ID or content matching
   - Has fallback mechanisms if FBref changes structure

3. **Data Normalization** - Maps FBref column codes to readable names
   - E.g., `gf` → `GF`, `opponent` → `Opponent`

4. **CSV Export** - Saves data to organized directory structure
   - Main tables go to root
   - Competitions split into subfolders
   - Match reports get individual folders

### Key Functions

| Function | Purpose |
|----------|---------|
| `_load_html()` | Selenium-based page loading with JavaScript support |
| `_extract_table_rows()` | Parse match log tables with fallback detection |
| `_extract_roster_rows()` | Extract player roster data |
| `_extract_standard_stats_table()` | Parse player statistics tables |
| `_save_match_report_tables()` | Download and save per-match detail data |
| `parse_team_from_stats_url()` | Extract squad_id/team_slug from URLs |
| `sanitize_filename()` | Create filesystem-safe filenames |

## ⚠️ Important Notes

### Performance
- **Single team**: ~5-10 minutes
- **Multiple teams**: ~30-60+ minutes (depends on number of matches)
- **Match reports** phase is the longest (each match needs individual page load)

### Rate Limiting
- FBref may block excessive requests. Add delays if needed:
  ```python
  time.sleep(2)  # Between requests
  ```
- Use `--headless` to make requests appear more natural

### Dynamic Content
- The script waits 8 seconds per page for JavaScript rendering
- Some data may not load if JavaScript changes on FBref
- Check console output for "WARNING" messages about missing tables

### Browser Requirements
- Requires Chrome/Chromium browser installed
- `webdriver-manager` automatically downloads correct Chrome driver version
- Works on Windows, macOS, Linux

## 🐛 Troubleshooting

### Issue: "No suitable match log table found"
**Cause:** FBref may have changed table structure  
**Solution:** Check FBref website to see if table exists, update table detection logic

### Issue: Chrome driver not found
**Cause:** Chrome/Chromium not installed  
**Solution:** Install Chrome from [google.com/chrome](https://google.com/chrome)

### Issue: "Season mismatch" error
**Cause:** URL season doesn't match `--season` argument  
**Solution:** Ensure both have same season format (e.g., both `2023-2024`)

### Issue: Empty CSV files
**Cause:** No data extracted from page  
**Solution:** 
- Verify FBref still has data for that team/season
- Check if table structure changed on FBref
- Try with `--headless false` to see browser activity

### Issue: Too many false timeouts
**Cause:** Slow internet connection  
**Solution:** Increase timeout in code:
```python
driver.set_page_load_timeout(60)  # Increase from 45
```

## 📚 Data Quality Notes

### Known Limitations

1. **Player Stats Not Always Available**
   - Some FBref pages don't have stats_standard tables
   - Script prints warning but continues processing

2. **Match Report Variations**
   - Not all matches have complete lineups/stats
   - Some older matches may have incomplete data

3. **Opponent Names**
   - May not have full stadium/location info
   - Column `stadium` and `where_they_play` are filled with "Unknown"

4. **International Cups**
   - Limited data for some international competitions

### Data Validation

- Remove rows where `Opponent` or `Date` are empty/null
- Check for duplicate matches (shouldn't exist)
- Verify match count matches expected season length

## 📖 API Reference

### FbrefPipeline Class

Main class handling the data extraction pipeline.

**Constructor:**
```python
FbrefPipeline(
    squad_id: str,           # FBref team ID
    season: str,             # Season (e.g., "2023-2024")
    team_slug: str,          # Team slug for URLs
    output_dir: Path,        # Output directory
    headless: bool = False,  # Run headless
    shooting_url: Optional[str] = None,  # Optional shooting data URL
    roster_url: Optional[str] = None     # Optional roster URL
)
```

**Main Method:**
```python
def run() -> None:
    """Execute the full pipeline."""
```

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- Add logging instead of print statements
- Implement concurrent request handling
- Add data validation/quality checks
- Support additional data sources
- Improve error handling and recovery


## 🔗 Links

- **FBref**: https://fbref.com
- **Python**: https://www.python.org
- **Selenium**: https://selenium.dev
- **BeautifulSoup**: https://www.crummy.com/software/BeautifulSoup

