"""
FORCE RE-EXTRACTOR: 2022-2025 MULTI-COMPETITION PLAYER PERFORMANCE DATA

Purpose:
- Re-extract all target seasons:
    - 2022-2023
    - 2023-2024
    - 2024-2025

- Dynamically fetch Premier League teams from API-Football.
- Ignore old checkpoint/state/season-complete markers.
- Ignore existing fixture IDs.
- Backup old CSVs before overwriting.
- Filter FA Cup to only fixtures involving at least one Premier League team.
- Filter Champions League to only fixtures involving at least one Premier League team.

API-Football season parameters:
- 2022 = 2022-2023 football season
- 2023 = 2023-2024 football season
- 2024 = 2024-2025 football season

Competitions extracted:
- Premier League
- FA Cup, only if at least one team is Premier League
- League Cup, all fixtures
- Champions League, only fixtures involving Premier League teams
- Community Shield, all fixtures

Outputs:
Data/API_SEASON_2022_2023/
Data/API_SEASON_2023_2024/
Data/API_SEASON_2024_2025/
"""

import requests
import pandas as pd
import time
import os
import shutil
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ============================================
# CONFIGURATION
# ============================================

load_dotenv()

API_BASE = "https://v3.football.api-sports.io"
API_KEY = os.getenv("APIFOOTBALL_KEY")

if not API_KEY:
    raise ValueError(
        "❌ APIFOOTBALL_KEY not found. "
        "Make sure your .env file contains APIFOOTBALL_KEY=your_key"
    )

HEADERS = {
    "x-apisports-key": API_KEY
}

# API-Football uses the season start year.
# 2022 = 2022-2023
# 2023 = 2023-2024
# 2024 = 2024-2025
SEASONS = [2022, 2023, 2024]

# Competition IDs
COMPETITIONS = {
    "Premier League": 39,
    "FA Cup": 45,
    "League Cup": 48,
    "Champions League": 2,
    "Community Shield": 528,
}

PREMIER_LEAGUE_ID = COMPETITIONS["Premier League"]

# Team-name aliases are not competition hard-coding.
# They only handle small naming differences between API responses.
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

DATA_PATH = Path(__file__).parent.parent / "Data"

FORCE_REEXTRACT = True
BACKUP_OLD_FILES = True

request_count = 0
start_time = time.time()

# Increase if API rate limits happen.
DELAY_BETWEEN_REQUESTS = 0.25

# Cache PL teams to avoid repeated API calls.
PL_TEAMS_CACHE = {}


# ============================================
# BASIC HELPERS
# ============================================

def get_season_label(api_season):
    """
    Convert API season parameter to folder/file label.

    Example:
    2023 -> 2023_2024
    """
    return f"{api_season}_{api_season + 1}"


def get_season_display(api_season):
    """
    Human-readable football season label.

    Example:
    2023 -> 2023-2024
    """
    return f"{api_season}-{api_season + 1}"


def log_progress(message, level="INFO"):
    """
    Print timestamped log messages.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {level}: {message}")


def normalize_team_name(team_name):
    """
    Standardise team names to improve matching across API responses.
    """
    if team_name is None:
        return None

    team_name = str(team_name).strip()
    return TEAM_NAME_ALIASES.get(team_name, team_name)


def get_output_dir(season):
    """
    Get or create the season-specific output directory.

    Example:
    season=2023 -> Data/API_SEASON_2023_2024/
    """
    season_label = get_season_label(season)
    output_dir = DATA_PATH / f"API_SEASON_{season_label}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def backup_existing_file(file_path):
    """
    Backup existing CSV before overwriting.
    """
    if not file_path.exists():
        return

    if not BACKUP_OLD_FILES:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = file_path.with_suffix(file_path.suffix + f".backup_{timestamp}")

    try:
        shutil.copy2(file_path, backup_path)
        log_progress(f"Backed up old file: {backup_path.name}")
    except Exception as e:
        log_progress(f"Could not backup {file_path.name}: {e}", "WARNING")


# ============================================
# API REQUESTS
# ============================================

def api_get(endpoint, params=None, retries=3, sleep_on_rate_limit=60):
    """
    Generic API-Football GET request with retries and rate-limit handling.
    """
    global request_count

    url = f"{API_BASE}{endpoint}"

    for attempt in range(1, retries + 1):
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                params=params,
                timeout=20,
            )

            request_count += 1
            time.sleep(DELAY_BETWEEN_REQUESTS)

            if response.status_code == 200:
                data = response.json()

                errors = data.get("errors")
                if errors:
                    log_progress(
                        f"API returned errors for {endpoint}, params={params}: {errors}",
                        "WARNING",
                    )

                return data.get("response", [])

            if response.status_code == 429:
                log_progress(
                    f"Rate limited on {endpoint}. Attempt {attempt}/{retries}. "
                    f"Waiting {sleep_on_rate_limit}s...",
                    "WARNING",
                )
                time.sleep(sleep_on_rate_limit)
                continue

            log_progress(
                f"HTTP {response.status_code} on {endpoint}, params={params}. "
                f"Attempt {attempt}/{retries}",
                "WARNING",
            )

        except requests.exceptions.Timeout:
            log_progress(
                f"Timeout on {endpoint}. Attempt {attempt}/{retries}",
                "WARNING",
            )
            time.sleep(5)

        except Exception as e:
            log_progress(
                f"Request error on {endpoint}: {e}. Attempt {attempt}/{retries}",
                "WARNING",
            )
            time.sleep(5)

    return []


def get_all_fixtures(competition_id, season):
    """
    Fetch all fixtures for a competition and API season.
    """
    params = {
        "league": competition_id,
        "season": season,
    }

    return api_get("/fixtures", params=params)


def get_fixture_info(fixture_id):
    """
    Fetch detailed fixture information for one fixture.
    """
    params = {
        "id": fixture_id
    }

    response = api_get("/fixtures", params=params)

    if response:
        return response[0]

    return None


def get_player_statistics(fixture_id):
    """
    Fetch detailed player statistics for one fixture.
    """
    params = {
        "fixture": fixture_id
    }

    response = api_get("/fixtures/players", params=params)

    return response or []


# ============================================
# DYNAMIC PREMIER LEAGUE TEAM FETCHING
# ============================================

def get_pl_teams_for_season(season):
    """
    Dynamically fetch all Premier League teams for a given API season
    from API-Football.

    Example:
    season=2023 -> Premier League teams from 2023-2024.

    Returns:
        set of normalized Premier League team names.
    """
    log_progress(
        f"Fetching Premier League teams dynamically for {get_season_display(season)}..."
    )

    params = {
        "league": PREMIER_LEAGUE_ID,
        "season": season,
    }

    response = api_get("/teams", params=params)

    teams = set()

    for item in response:
        team = item.get("team", {})
        team_name = normalize_team_name(team.get("name"))

        if team_name:
            teams.add(team_name)

    if teams:
        log_progress(
            f"✅ Fetched {len(teams)} Premier League teams for "
            f"{get_season_display(season)}: {sorted(teams)}"
        )
    else:
        log_progress(
            f"⚠️ No Premier League teams found from /teams endpoint for season {season}",
            "WARNING",
        )

    if len(teams) != 20:
        log_progress(
            f"⚠️ Expected 20 Premier League teams for {get_season_display(season)}, "
            f"but found {len(teams)}. The script will continue.",
            "WARNING",
        )

    return teams


def get_pl_teams_cached(season):
    """
    Fetch Premier League teams with caching to avoid repeated API calls.
    """
    if season not in PL_TEAMS_CACHE:
        PL_TEAMS_CACHE[season] = get_pl_teams_for_season(season)

    return PL_TEAMS_CACHE[season]


# ============================================
# COMPETITION-SPECIFIC FILTERING
# ============================================

def filter_competition_fixtures(fixtures, competition_name, season):
    """
    Filter fixtures depending on competition.

    Rules:
    - Premier League:
        Keep all fixtures.

    - FA Cup:
        Keep only fixtures where at least one team is from the Premier League.

    - League Cup:
        Keep all fixtures.

    - Community Shield:
        Keep all fixtures.

    - Champions League:
        Keep only fixtures where at least one team is from the Premier League.
        This dynamically keeps English UCL teams and excludes non-English-only fixtures.
    """

    pl_teams = get_pl_teams_cached(season)

    if not pl_teams:
        log_progress(
            f"⚠️ Could not derive Premier League teams for {get_season_display(season)}. "
            f"Keeping all fixtures for {competition_name} to avoid accidental data loss.",
            "WARNING",
        )
        return fixtures

    # -------------------------
    # Premier League
    # -------------------------
    if competition_name == "Premier League":
        log_progress(f"Premier League: kept all {len(fixtures)} fixtures")
        return fixtures

    # -------------------------
    # FA Cup
    # -------------------------
    if competition_name == "FA Cup":
        filtered = []

        for fixture in fixtures:
            home_team = normalize_team_name(
                fixture.get("teams", {}).get("home", {}).get("name")
            )
            away_team = normalize_team_name(
                fixture.get("teams", {}).get("away", {}).get("name")
            )

            if home_team in pl_teams or away_team in pl_teams:
                filtered.append(fixture)

        log_progress(
            f"FA Cup: kept {len(filtered)} of {len(fixtures)} fixtures "
            f"because at least one team is Premier League"
        )

        return filtered

    # -------------------------
    # League Cup
    # -------------------------
    if competition_name == "League Cup":
        log_progress(f"League Cup: kept all {len(fixtures)} fixtures")
        return fixtures

    # -------------------------
    # Community Shield
    # -------------------------
    if competition_name == "Community Shield":
        log_progress(f"Community Shield: kept all {len(fixtures)} fixtures")
        return fixtures

    # -------------------------
    # Champions League
    # -------------------------
    if competition_name == "Champions League":
        filtered = []

        for fixture in fixtures:
            home_team = normalize_team_name(
                fixture.get("teams", {}).get("home", {}).get("name")
            )
            away_team = normalize_team_name(
                fixture.get("teams", {}).get("away", {}).get("name")
            )

            if home_team in pl_teams or away_team in pl_teams:
                filtered.append(fixture)

        log_progress(
            f"Champions League: kept {len(filtered)} of {len(fixtures)} fixtures "
            f"involving Premier League teams"
        )

        return filtered

    log_progress(
        f"No specific filter for {competition_name}; keeping all fixtures",
        "WARNING",
    )

    return fixtures


def diagnose_filtered_fixtures(fixtures, competition_name, season):
    """
    Print retained fixture list after filtering.
    Useful for checking FA Cup and Champions League behavior.
    """
    log_progress("=" * 80)
    log_progress(
        f"DIAGNOSTIC: Retained fixtures for {competition_name} {get_season_display(season)}"
    )
    log_progress("=" * 80)

    rows = []

    for fixture in fixtures:
        rows.append(
            {
                "fixture_id": fixture.get("fixture", {}).get("id"),
                "date": fixture.get("fixture", {}).get("date"),
                "round": fixture.get("league", {}).get("round", ""),
                "home_team": fixture.get("teams", {}).get("home", {}).get("name"),
                "away_team": fixture.get("teams", {}).get("away", {}).get("name"),
            }
        )

    if not rows:
        log_progress(f"No retained fixtures for {competition_name}", "WARNING")
        return

    diag_df = pd.DataFrame(rows).sort_values("date")
    print(diag_df.to_string(index=False))


def validate_champions_league_fixture_coverage(fixtures, season):
    """
    Dynamically validate which Premier League teams appear
    in retained Champions League fixtures.
    """
    pl_teams = get_pl_teams_cached(season)

    counts = {team: 0 for team in pl_teams}

    for fixture in fixtures:
        home_team = normalize_team_name(
            fixture.get("teams", {}).get("home", {}).get("name")
        )
        away_team = normalize_team_name(
            fixture.get("teams", {}).get("away", {}).get("name")
        )

        for team in pl_teams:
            if home_team == team or away_team == team:
                counts[team] += 1

    pl_teams_in_ucl = {
        team: count
        for team, count in counts.items()
        if count > 0
    }

    log_progress("Premier League teams found in retained Champions League fixtures:")

    if not pl_teams_in_ucl:
        log_progress(
            "⚠️ No Premier League teams found in Champions League fixtures.",
            "WARNING",
        )
    else:
        for team, count in sorted(pl_teams_in_ucl.items()):
            log_progress(f"  - {team}: {count} fixtures")

    return pl_teams_in_ucl


# ============================================
# RECORD EXTRACTION
# ============================================

def safe_pass_accuracy(value):
    """
    Convert pass accuracy from API format to numeric.
    Handles values like '85%', 85, None.
    """
    if value is None:
        return 0

    if isinstance(value, str):
        value = value.strip()
        if value.endswith("%"):
            value = value[:-1]
        try:
            return float(value)
        except ValueError:
            return 0

    try:
        return float(value)
    except Exception:
        return 0


def extract_player_record(player_data, team_name, fixture_info, competition):
    """
    Parse one player into a flat standardized record.
    """

    player = player_data.get("player", {})
    stats_list = player_data.get("statistics", [])

    if not stats_list:
        return None

    stats = stats_list[0]

    games = stats.get("games", {})
    shots = stats.get("shots", {})
    goals = stats.get("goals", {})
    passes = stats.get("passes", {})
    tackles = stats.get("tackles", {})
    duels = stats.get("duels", {})
    dribbles = stats.get("dribbles", {})
    fouls = stats.get("fouls", {})
    cards = stats.get("cards", {})

    record = {
        "fixture_id": fixture_info["fixture"]["id"],
        "date": fixture_info["fixture"]["date"],
        "competition": competition,
        "season": fixture_info["league"]["season"],
        "round": fixture_info["league"].get("round", ""),
        "home_team": fixture_info["teams"]["home"]["name"],
        "away_team": fixture_info["teams"]["away"]["name"],
        "player_team": team_name,
        "player_id": player.get("id"),
        "player_name": player.get("name"),
        "player_number": games.get("number"),
        "player_position": games.get("position"),
        "minutes_played": games.get("minutes") or 0,
        "rating": games.get("rating") or 0,
        "is_captain": games.get("captain", False),
        "is_substitute": games.get("substitute", False),
        "shots_total": shots.get("total") or 0,
        "shots_on_target": shots.get("on") or 0,
        "goals": goals.get("total") or 0,
        "assists": goals.get("assists") or 0,
        "passes_total": passes.get("total") or 0,
        "passes_key": passes.get("key") or 0,
        "passes_accuracy": safe_pass_accuracy(passes.get("accuracy")),
        "dribbles_attempts": dribbles.get("attempts") or 0,
        "dribbles_success": dribbles.get("success") or 0,
        "tackles_total": tackles.get("total") or 0,
        "tackles_blocks": tackles.get("blocks") or 0,
        "tackles_interceptions": tackles.get("interceptions") or 0,
        "duels_total": duels.get("total") or 0,
        "duels_won": duels.get("won") or 0,
        "fouls_drawn": fouls.get("drawn") or 0,
        "fouls_committed": fouls.get("committed") or 0,
        "cards_yellow": cards.get("yellow") or 0,
        "cards_red": cards.get("red") or 0,
    }

    return record


def extract_team_records(fixture_info, competition):
    """
    Extract two team-level records:
    - one for the home team
    - one for the away team
    """

    home_goals = fixture_info["goals"]["home"]
    away_goals = fixture_info["goals"]["away"]

    if home_goals is None or away_goals is None:
        return []

    if home_goals > away_goals:
        home_result, away_result = "Win", "Loss"
        home_points, away_points = 3, 0
    elif home_goals < away_goals:
        home_result, away_result = "Loss", "Win"
        home_points, away_points = 0, 3
    else:
        home_result, away_result = "Draw", "Draw"
        home_points, away_points = 1, 1

    home_stats = {}
    away_stats = {}

    if "statistics" in fixture_info and fixture_info["statistics"]:
        if len(fixture_info["statistics"]) > 0:
            for stat in fixture_info["statistics"][0].get("statistics", []):
                stat_type = stat.get("type", "").lower().replace(" ", "_")
                stat_value = stat.get("value")
                if stat_value is not None:
                    home_stats[f"home_{stat_type}"] = stat_value

        if len(fixture_info["statistics"]) > 1:
            for stat in fixture_info["statistics"][1].get("statistics", []):
                stat_type = stat.get("type", "").lower().replace(" ", "_")
                stat_value = stat.get("value")
                if stat_value is not None:
                    away_stats[f"away_{stat_type}"] = stat_value

    home_record = {
        "fixture_id": fixture_info["fixture"]["id"],
        "date": fixture_info["fixture"]["date"],
        "competition": competition,
        "season": fixture_info["league"]["season"],
        "round": fixture_info["league"].get("round", ""),
        "team_name": fixture_info["teams"]["home"]["name"],
        "team_id": fixture_info["teams"]["home"]["id"],
        "is_home": True,
        "opponent": fixture_info["teams"]["away"]["name"],
        "opponent_id": fixture_info["teams"]["away"]["id"],
        "goals_for": home_goals,
        "goals_against": away_goals,
        "result": home_result,
        "points": home_points,
        "status": fixture_info["fixture"]["status"]["short"],
    }
    home_record.update(home_stats)

    away_record = {
        "fixture_id": fixture_info["fixture"]["id"],
        "date": fixture_info["fixture"]["date"],
        "competition": competition,
        "season": fixture_info["league"]["season"],
        "round": fixture_info["league"].get("round", ""),
        "team_name": fixture_info["teams"]["away"]["name"],
        "team_id": fixture_info["teams"]["away"]["id"],
        "is_home": False,
        "opponent": fixture_info["teams"]["home"]["name"],
        "opponent_id": fixture_info["teams"]["home"]["id"],
        "goals_for": away_goals,
        "goals_against": home_goals,
        "result": away_result,
        "points": away_points,
        "status": fixture_info["fixture"]["status"]["short"],
    }
    away_record.update(away_stats)

    return [home_record, away_record]


# ============================================
# COMPETITION EXTRACTION
# ============================================

def extract_competition_data(competition_name, competition_id, season):
    """
    Extract player and team records for one competition and one season.

    This force version does NOT skip:
    - completed seasons
    - completed competitions
    - existing fixture IDs
    """

    log_progress(f"Fetching fixtures for {competition_name} - API season {season}...")

    fixtures = get_all_fixtures(competition_id, season)

    log_progress(
        f"{competition_name}: API returned {len(fixtures)} fixtures before filtering"
    )

    fixtures = filter_competition_fixtures(
        fixtures=fixtures,
        competition_name=competition_name,
        season=season,
    )

    if competition_name in {"FA Cup", "Champions League"}:
        diagnose_filtered_fixtures(fixtures, competition_name, season)

    if competition_name == "Champions League":
        validate_champions_league_fixture_coverage(fixtures, season)

    if not fixtures:
        log_progress(
            f"No fixtures retained for {competition_name} season {season}",
            "WARNING",
        )
        return [], []

    log_progress(f"✅ Extracting {len(fixtures)} fixtures for {competition_name}")

    player_records = []
    team_records = []

    for idx, fixture in enumerate(fixtures, 1):
        fixture_id = fixture["fixture"]["id"]

        home_team = fixture.get("teams", {}).get("home", {}).get("name")
        away_team = fixture.get("teams", {}).get("away", {}).get("name")
        fixture_date = fixture.get("fixture", {}).get("date")

        log_progress(
            f"[{get_season_label(season)} | {competition_name}] "
            f"{idx}/{len(fixtures)} fixture_id={fixture_id}: "
            f"{home_team} vs {away_team} ({fixture_date})"
        )

        fixture_info = get_fixture_info(fixture_id)

        if not fixture_info:
            log_progress(f"Skipping fixture {fixture_id}: no fixture_info", "WARNING")
            continue

        teams_data = get_player_statistics(fixture_id)

        if not teams_data:
            log_progress(f"No player statistics for fixture {fixture_id}", "WARNING")

        for team_data in teams_data:
            if not team_data:
                continue

            team_name = team_data.get("team", {}).get("name", "")
            players = team_data.get("players", [])

            for player_data in players:
                record = extract_player_record(
                    player_data=player_data,
                    team_name=team_name,
                    fixture_info=fixture_info,
                    competition=competition_name,
                )

                if record:
                    player_records.append(record)

        team_records_pair = extract_team_records(fixture_info, competition_name)
        team_records.extend(team_records_pair)

    log_progress(
        f"✅ Finished {competition_name} {get_season_label(season)}: "
        f"{len(player_records)} player records, {len(team_records)} team records"
    )

    return player_records, team_records


# ============================================
# SAVING
# ============================================

def save_dataframe(df, output_file):
    """
    Save dataframe to CSV with backup/overwrite.
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if output_file.exists():
        backup_existing_file(output_file)

    df.to_csv(output_file, index=False)
    log_progress(f"✅ Saved {len(df)} rows to {output_file}")


def save_season_outputs(season, season_player_records, season_team_records):
    """
    Save combined and per-competition CSVs for one season.
    """
    season_label = get_season_label(season)
    output_dir = get_output_dir(season)

    player_df = pd.DataFrame(season_player_records)
    team_df = pd.DataFrame(season_team_records)

    if player_df.empty:
        log_progress(f"No combined player data to save for {season_label}.", "WARNING")
    else:
        save_dataframe(
            player_df,
            output_dir / f"multi_competition_player_stats_{season_label}.csv",
        )

    if team_df.empty:
        log_progress(f"No combined team data to save for {season_label}.", "WARNING")
    else:
        save_dataframe(
            team_df,
            output_dir / f"multi_competition_team_results_{season_label}.csv",
        )

    for competition_name in COMPETITIONS.keys():
        safe_comp_name = competition_name.lower().replace(" ", "_")

        if not player_df.empty:
            comp_player_df = player_df[player_df["competition"] == competition_name].copy()

            if not comp_player_df.empty:
                save_dataframe(
                    comp_player_df,
                    output_dir / f"player_stats_{safe_comp_name}_{season_label}.csv",
                )

        if not team_df.empty:
            comp_team_df = team_df[team_df["competition"] == competition_name].copy()

            if not comp_team_df.empty:
                save_dataframe(
                    comp_team_df,
                    output_dir / f"team_results_{safe_comp_name}_{season_label}.csv",
                )

    return player_df, team_df


# ============================================
# FINAL VALIDATION
# ============================================

def validate_final_outputs(player_df, team_df, season):
    """
    Validate important output properties season by season.
    """
    season_label = get_season_label(season)

    log_progress("=" * 80)
    log_progress(f"FINAL VALIDATION: {season_label}")
    log_progress("=" * 80)

    if player_df.empty:
        log_progress(f"❌ Player dataframe is empty for {season_label}.", "ERROR")
        return

    if team_df.empty:
        log_progress(f"⚠️ Team dataframe is empty for {season_label}.", "WARNING")

    pl_teams = get_pl_teams_cached(season)

    log_progress(f"Total player rows: {len(player_df):,}")
    log_progress(f"Total team rows: {len(team_df):,}")

    log_progress("Player rows by competition:")
    print(player_df["competition"].value_counts().sort_index())

    if not team_df.empty:
        log_progress("Team rows by competition:")
        print(team_df["competition"].value_counts().sort_index())

    # Validate FA Cup filtering
    if "FA Cup" in player_df["competition"].unique():
        fa_player = player_df[player_df["competition"] == "FA Cup"].copy()

        fa_fixtures = (
            fa_player[["fixture_id", "home_team", "away_team"]]
            .drop_duplicates()
            .copy()
        )

        invalid_fa = []

        for _, row in fa_fixtures.iterrows():
            home_team = normalize_team_name(row["home_team"])
            away_team = normalize_team_name(row["away_team"])

            if home_team not in pl_teams and away_team not in pl_teams:
                invalid_fa.append(row.to_dict())

        if invalid_fa:
            log_progress(
                f"⚠️ Found {len(invalid_fa)} FA Cup fixtures with no PL team.",
                "WARNING",
            )
            print(pd.DataFrame(invalid_fa).to_string(index=False))
        else:
            log_progress(
                "✅ FA Cup validation passed: every retained FA Cup fixture has at least one PL team."
            )

    # Validate Champions League filtering dynamically
    if "Champions League" in player_df["competition"].unique():
        cl_player = player_df[player_df["competition"] == "Champions League"].copy()

        player_teams = set(
            cl_player["player_team"]
            .dropna()
            .map(normalize_team_name)
            .unique()
        )

        found_pl_ucl_teams = pl_teams.intersection(player_teams)

        log_progress(
            f"Premier League teams found in Champions League player rows: "
            f"{sorted(found_pl_ucl_teams)}"
        )

        if not found_pl_ucl_teams:
            log_progress(
                "⚠️ No Premier League teams found in Champions League player rows.",
                "WARNING",
            )
        else:
            log_progress(
                "✅ Champions League validation passed: Premier League teams found dynamically."
            )

        log_progress("Champions League player rows by team:")
        print(cl_player["player_team"].value_counts().sort_index())


# ============================================
# MAIN
# ============================================

def main():
    """
    Force re-extract all target seasons.
    """

    log_progress("")
    log_progress("=" * 80)
    log_progress("FORCE RE-EXTRACTION: ALL TARGET SEASONS")
    log_progress("=" * 80)
    log_progress("API seasons: 2022, 2023, 2024")
    log_progress("Football seasons: 2022-2023, 2023-2024, 2024-2025")
    log_progress("Ignoring extraction_state_checkpoint.json")
    log_progress("Ignoring .SEASON_COMPLETE markers")
    log_progress("Ignoring existing fixture IDs")
    log_progress("Existing CSVs will be backed up and overwritten")
    log_progress("Premier League teams are fetched dynamically from API-Football")
    log_progress("FA Cup filter: keep only fixtures with at least one PL team")
    log_progress("Champions League filter: keep only fixtures with at least one PL team")
    log_progress("=" * 80)

    all_player_dfs = []
    all_team_dfs = []

    for season in SEASONS:
        season_start_time = time.time()
        season_label = get_season_label(season)

        log_progress("")
        log_progress("=" * 80)
        log_progress(f"STARTING SEASON {season_label}")
        log_progress("=" * 80)

        # Fetch PL teams once at season start.
        pl_teams = get_pl_teams_cached(season)

        if not pl_teams:
            log_progress(
                f"⚠️ Premier League team list could not be fetched for {season_label}. "
                f"Filtering may be less strict for domestic cups.",
                "WARNING",
            )

        season_player_records = []
        season_team_records = []

        for competition_name, competition_id in COMPETITIONS.items():
            log_progress("")
            log_progress("-" * 80)
            log_progress(f"Extracting {competition_name} for {season_label}")
            log_progress("-" * 80)

            try:
                player_data, team_data = extract_competition_data(
                    competition_name=competition_name,
                    competition_id=competition_id,
                    season=season,
                )

                season_player_records.extend(player_data)
                season_team_records.extend(team_data)

                log_progress(
                    f"✅ {competition_name} complete for {season_label}: "
                    f"{len(player_data)} player records, {len(team_data)} team records"
                )

            except Exception as e:
                log_progress(
                    f"❌ Error extracting {competition_name} for {season_label}: {e}",
                    "ERROR",
                )
                continue

        log_progress("")
        log_progress("=" * 80)
        log_progress(f"SAVING OUTPUTS FOR {season_label}")
        log_progress("=" * 80)

        player_df, team_df = save_season_outputs(
            season=season,
            season_player_records=season_player_records,
            season_team_records=season_team_records,
        )

        validate_final_outputs(player_df, team_df, season)

        if not player_df.empty:
            all_player_dfs.append(player_df)

        if not team_df.empty:
            all_team_dfs.append(team_df)

        season_elapsed = time.time() - season_start_time

        log_progress("")
        log_progress("=" * 80)
        log_progress(f"SEASON COMPLETE: {season_label}")
        log_progress("=" * 80)
        log_progress(f"Player records: {len(player_df):,}")
        log_progress(f"Team records: {len(team_df):,}")
        log_progress(f"Season elapsed time: {season_elapsed / 60:.2f} minutes")
        log_progress(f"Output folder: {get_output_dir(season)}")
        log_progress("=" * 80)

    # Combined summary across all seasons
    log_progress("")
    log_progress("=" * 80)
    log_progress("ALL-SEASON EXTRACTION SUMMARY")
    log_progress("=" * 80)

    if all_player_dfs:
        combined_player_df = pd.concat(all_player_dfs, ignore_index=True)
        log_progress(f"Combined player rows across all seasons: {len(combined_player_df):,}")
        log_progress("Combined player rows by season:")
        print(combined_player_df["season"].value_counts().sort_index())
        log_progress("Combined player rows by competition:")
        print(combined_player_df["competition"].value_counts().sort_index())
    else:
        log_progress("No player data extracted across seasons.", "WARNING")

    if all_team_dfs:
        combined_team_df = pd.concat(all_team_dfs, ignore_index=True)
        log_progress(f"Combined team rows across all seasons: {len(combined_team_df):,}")
        log_progress("Combined team rows by season:")
        print(combined_team_df["season"].value_counts().sort_index())
        log_progress("Combined team rows by competition:")
        print(combined_team_df["competition"].value_counts().sort_index())
    else:
        log_progress("No team data extracted across seasons.", "WARNING")

    elapsed = time.time() - start_time

    log_progress("")
    log_progress("=" * 80)
    log_progress("RE-EXTRACTION COMPLETE FOR ALL SEASONS")
    log_progress("=" * 80)
    log_progress(f"Total API requests: {request_count}")
    log_progress(f"Total elapsed time: {elapsed / 60:.2f} minutes")
    log_progress(f"Data root folder: {DATA_PATH}")
    log_progress("=" * 80)


if __name__ == "__main__":
    main()