#!/usr/bin/env python3

"""
Run football_data_pipeline.py for multiple teams in parallel (Season 2021-2022)
"""

import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ⚠️ ADD YOUR SCRAPE.DO TOKEN HERE
SCRAPE_DO_TOKEN = "8f0c5295d7af4a5cb0c08eef4294fa6ddcf073d2021"

# Define teams with their URLs and squad IDs for 2021-2022 season
TEAMS = {
    "Manchester-City": {
        "url": "https://fbref.com/en/squads/b8fd03ef/2021-2022/all_comps/Manchester-City-Stats-All-Competitions",
        "season": "2021-2022"
    },
    "Manchester-United": {
        "url": "https://fbref.com/en/squads/19538871/2021-2022/all_comps/Manchester-United-Stats-All-Competitions",
        "season": "2021-2022"
    },
    "Liverpool": {
        "url": "https://fbref.com/en/squads/822bd0ba/2021-2022/all_comps/Liverpool-Stats-All-Competitions",
        "season": "2021-2022"
    },
    "Chelsea": {
        "url": "https://fbref.com/en/squads/cff3d9bb/2021-2022/all_comps/Chelsea-Stats-All-Competitions",
        "season": "2021-2022"
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
    
    # Add scrape.do token if provided
    if SCRAPE_DO_TOKEN:
        cmd.extend(["--scrape-do-token", SCRAPE_DO_TOKEN])
        print(f"  Using scrape.do token: {SCRAPE_DO_TOKEN[:10]}...")
    else:
        print(f"  No scrape.do token provided (will try fallback methods)")
    
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
    print("FOOTBALL DATA PIPELINE - MULTI-TEAM EXTRACTION (2021-2022)")
    print("="*70)
    print(f"\nTeams to process: {list(TEAMS.keys())}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Season: 2021-2022")
    
    if not SCRAPE_DO_TOKEN:
        print("\n" + "!"*70)
        print("⚠️  NOTE: No scrape.do token configured")
        print("!"*70)
        print("""
FBref (Football Reference) actively blocks automated scraping.
For reliable extraction, set SCRAPE_DO_TOKEN at the top of this file.

Get a free token at: https://www.scrape.do (free tier available)
Then add it to line 11: SCRAPE_DO_TOKEN = "your_token_here"

Without a token, the script will attempt cloudscraper and Selenium fallbacks
(which may not work due to Cloudflare and HTTP 403 blocks).
""")
        print("!"*70 + "\n")
    else:
        print(f"\n✓ Using scrape.do for reliable FBref access\n")
    
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
