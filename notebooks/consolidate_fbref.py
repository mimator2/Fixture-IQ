#!/usr/bin/env python3
from pathlib import Path
import re
import pandas as pd

KNOWN_COMPETITIONS = [
    "fa_community_shield",
    "champions_lg",
    "community_shield",
    "super_cup",
    "premier_league",
    "efl_cup",
    "fa_cup",
]


def parse_file_name_details(file_name: str, folder_name: str | None = None) -> tuple[str, str, str]:
    """
    Parses match metadata from either the CSV file name or its parent match folder.
    Preferred source: folder name inside match_reports, e.g. 2025-04-05_premier_league_everton

    Returns:
        tuple: (match_date, competition, opponent)
    """
    source = folder_name or file_name
    source = source.removesuffix(".csv")

    folder_match = re.match(r"^(\d{4}-\d{2}-\d{2})_(.+)$", source)
    if not folder_match:
        return "Unknown", "Unknown", "Unknown"

    match_date = folder_match.group(1)
    remainder = folder_match.group(2)

    for comp in sorted(KNOWN_COMPETITIONS, key=len, reverse=True):
        prefix = comp + "_"
        if remainder.startswith(prefix):
            competition = comp.replace("_", " ").title()
            opponent = remainder[len(prefix):].replace("_", " ").title()
            return match_date, competition, opponent

    # Fallback: assume the first two tokens are competition and the rest is opponent
    parts = remainder.split("_")
    if len(parts) >= 3:
        competition = " ".join(parts[:2]).title()
        opponent = " ".join(parts[2:]).title()
        return match_date, competition, opponent

    return "Unknown", "Unknown", "Unknown"

def consolidate_fbref_per_season_team(root_data_dir: Path):
    print(f"🔍 Scanning root Data directory: {root_data_dir.resolve()}")
    
    # Target all CSVs inside any season's match_reports folders
    # Pattern: Data/{season}/fbref/{team_folder}/match_reports/{match_folder}/*.csv
    csv_paths = list(root_data_dir.glob("*/fbref/*/match_reports/**/*.csv"))
    
    if not csv_paths:
        print("❌ No matching CSV files found. Please check your data directory structure.")
        return

    # Dictionary structure: (season, team_folder) -> file_type -> list of DataFrames
    grouped_data = {}

    for csv_path in csv_paths:
        file_name = csv_path.name
        
        # Determine file type group based on terminations
        file_type = None
        if file_name.endswith("goalkeeper_stats.csv"):
            file_type = "goalkeeper_stats"
        elif file_name.endswith("lineups.csv"):
            file_type = "lineups"
        elif file_name.endswith("player_stats.csv"):
            file_type = "player_stats"
        
        if not file_type:
            continue
            
        # Extract season and team folder from hierarchy:
        # csv_path.parents[2] -> {team_folder} (e.g., arsenal_2023_2024)
        # csv_path.parents[4] -> {season}      (e.g., 2023-2024)
        team_folder = csv_path.parents[2].name
        season = csv_path.parents[4].name
        
        # Clean up team name formatting to use as a human-readable column value
        tracked_team_name = team_folder.replace('_', ' ').replace(season.replace('-', '_'), '').strip('_').title()

        # Parse the specific match details from the parent match folder name
        match_folder_name = csv_path.parent.name
        match_date, competition, opponent = parse_file_name_details(file_name, match_folder_name)
        
        try:
            df = pd.read_csv(csv_path)
            if df.empty:
                continue
                
            # Inject descriptive tracking metadata columns
            df.insert(0, "season", season)
            df.insert(1, "tracked_team", tracked_team_name)
            df.insert(2, "match_date", match_date)
            df.insert(3, "competition", competition)
            df.insert(4, "opponent_team", opponent)
            df.insert(5, "original_file", file_name)
            
            # Use unique (season, team_folder) combination as key to isolate data per season
            group_key = (season, team_folder)
            if group_key not in grouped_data:
                grouped_data[group_key] = {
                    "goalkeeper_stats": [],
                    "lineups": [],
                    "player_stats": []
                }
                
            grouped_data[group_key][file_type].append(df)
            
        except Exception as e:
            print(f"⚠️ Error reading file {file_name}: {e}")

    # Process and save grouped data back into their respective seasonal team folders
    print("\n💾 Merging and saving files into respective team season directories...")
    
    for (season, team_folder), categories in grouped_data.items():
        # Destination directory: Data/{season}/fbref/{team_folder}/match_reports
        team_output_dir = root_data_dir / season / "fbref" / team_folder / "match_reports"
        team_output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📂 Writing master files for: {season} ➔ {team_folder}")
        
        for file_type, df_list in categories.items():
            if df_list:
                combined_df = pd.concat(df_list, ignore_index=True)
                
                # Naming format: master_{file_type}.csv
                output_file = team_output_dir / f"master_{file_type}.csv"
                combined_df.to_csv(output_file, index=False)
                print(f"  ✅ master_{file_type}.csv: {len(combined_df)} rows saved.")
            else:
                print(f"  ⚠️ No files found for {file_type}")

if __name__ == "__main__":
    # Point this to the root "Data" directory containing your seasonal folders
    ROOT_DATA_DIR = Path("Data") 
    
    consolidate_fbref_per_season_team(ROOT_DATA_DIR)