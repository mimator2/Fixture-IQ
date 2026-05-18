#!/usr/bin/env python3
"""
Run football_data_pipeline.py for multiple teams in parallel (Season 2022-2023)
"""

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Define teams with their URLs and squad IDs for 2022-2023 season
TEAMS = {
    "Manchester-City": {
        "url": "https://fbref.com/en/squads/b8fd03ef/2022-2023/all_comps/Manchester-City-Stats-All-Competitions",
        "season": "2022-2023"
    },
    "Liverpool": {
        "url": "https://fbref.com/en/squads/822bd0ba/2022-2023/all_comps/Liverpool-Stats-All-Competitions",
        "season": "2022-2023"
    },
    "Chelsea": {
        "url": "https://fbref.com/en/squads/cff3d9bb/2022-2023/all_comps/Chelsea-Stats-All-Competitions",
        "season": "2022-2023"
    },
    "Tottenham-Hotspur": {
        "url": "https://fbref.com/en/squads/361ca564/2022-2023/all_comps/Tottenham-Hotspur-Stats-All-Competitions",
        "season": "2022-2023"
    }
}

OUTPUT_DIR = "Data"
SCRIPT_PATH = "football_data_pipeline.py"


def run_team_extraction(team_name, team_info):
    """Run pipeline for a single team"""
    print(f"\n{'='*70}")
    print(f"Starting extraction for: {team_name}")
    print(f"{'='*70}")
    
    cmd = [
        "python",
        SCRIPT_PATH,
        "--team-url", team_info["url"],
        "--season", team_info["season"],
        "--output-dir", OUTPUT_DIR,
        "--headless"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=False, text=True, timeout=3600)
        if result.returncode == 0:
            print(f"\n✅ {team_name} extraction COMPLETED successfully")
            return (team_name, "SUCCESS")
        else:
            print(f"\n❌ {team_name} extraction FAILED with exit code {result.returncode}")
            return (team_name, "FAILED")
    except subprocess.TimeoutExpired:
        print(f"\n⏱️ {team_name} extraction TIMED OUT after 1 hour")
        return (team_name, "TIMEOUT")
    except Exception as e:
        print(f"\n❌ {team_name} extraction ERROR: {str(e)}")
        return (team_name, "ERROR")


def main():
    """Run teams sequentially with delays to avoid rate limiting"""
    print("\n" + "="*70)
    print("FOOTBALL DATA PIPELINE - MULTI-TEAM EXTRACTION (2022-2023)")
    print("="*70)
    print(f"\nTeams to process: {list(TEAMS.keys())}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Season: 2022-2023")
    
    # Create output directory if it doesn't exist
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # Run extractions SEQUENTIALLY with delays to avoid FBref rate limiting
    print(f"\n🚀 Starting sequential extraction for {len(TEAMS)} teams (with 10s delays)...\n")
    
    results = {}
    for idx, (team_name, team_info) in enumerate(TEAMS.items()):
        if idx > 0:
            delay = 10
            print(f"\n⏳ Waiting {delay}s before next team (to avoid rate limiting)...")
            time.sleep(delay)
        
        team_name, status = run_team_extraction(team_name, team_info)
        results[team_name] = status
    
    # Print final summary
    print("\n" + "="*70)
    print("EXTRACTION SUMMARY")
    print("="*70)
    
    for team_name, status in sorted(results.items()):
        status_symbol = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "⏱️"
        print(f"{status_symbol} {team_name:20s}: {status}")
    
    success_count = sum(1 for s in results.values() if s == "SUCCESS")
    total_count = len(results)
    print(f"\n📊 Overall: {success_count}/{total_count} teams extracted successfully")
    
    if success_count == total_count:
        print("\n🎉 All teams extracted successfully!")
        return 0
    else:
        print(f"\n⚠️ {total_count - success_count} team(s) failed. Check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
