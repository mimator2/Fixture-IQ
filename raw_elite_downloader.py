#!/usr/bin/env python3
"""
FixtureIQ PL-Centric Raw Match Downloader
========================================================================
Pulls raw per-match player tables ONLY for fixtures involving PL teams.
  - All English Premier League games.
  - Champions League games where at least one team is from the PL.
========================================================================
"""

import argparse
import os
import time
from pathlib import Path
import pandas as pd
import ScraperFC

# Force Edge browser execution to bypass Cloudflare
os.environ["BOTASAURUS_CHROME_EXECUTABLE_PATH"] = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

def download_pl_centric_matches(year_ss: str, output_dir: str, delay: float):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    season_str = year_ss.replace("/", "_")
    output_file = output_path / f"raw_pl_centric_player_matches_{season_str}.csv"
    
    print(f"\n{'='*75}")
    print(f" PURE RAW DATA DOWNLOADER: PREMIER LEAGUE CENTRIC SCOPE")
    print(f" Target Season : {year_ss}")
    print(f"{'='*75}")
    
    print("[*] Initializing ScraperFC Automation Engine...")
    scraper = ScraperFC.Sofascore()
    
    # Step 1: Fetch the Premier League calendar to discover all PL teams
    print("[*] Discovering Premier League teams...")
    try:
        pl_matches = scraper.get_match_dicts(year_ss, "England Premier League")
        print(f"    [✅] Found {len(pl_matches)} domestic Premier League fixtures.")
    except Exception as e:
        print(f"    [❌] Failed to fetch Premier League calendar: {e}")
        return

    # Build a set of all team names playing in the Premier League this season
    pl_teams = set()
    for match in pl_matches:
        home = match.get('homeTeam', {}).get('name')
        away = match.get('awayTeam', {}).get('name')
        if home: pl_teams.add(home)
        if away: pl_teams.add(away)
        
    print(f"    [📊] Identified {len(pl_teams)} unique Premier League clubs.")
    
    # Master dictionary to hold target matches to scrape, indexed by SofaScore ID
    target_fixtures = {}
    
    # Add all Premier League matches automatically
    for match in pl_matches:
        m_id = match.get('id')
        if m_id:
            match['origin_competition'] = "England Premier League"
            target_fixtures[m_id] = match

    # Step 2: Fetch Champions League calendar and filter strictly by PL teams
    print("[*] Fetching Champions League calendar to scan for PL clubs...")
    try:
        ucl_matches = scraper.get_match_dicts(year_ss, "UEFA Champions League")
        ucl_filtered_count = 0
        
        for match in ucl_matches:
            m_id = match.get('id')
            home = match.get('homeTeam', {}).get('name')
            away = match.get('awayTeam', {}).get('name')
            
            # CRITICAL FILTER: Is either the home team or away team a PL club?
            if home in pl_teams or away in pl_teams:
                if m_id and m_id not in target_fixtures:
                    match['origin_competition'] = "UEFA Champions League"
                    target_fixtures[m_id] = match
                    ucl_filtered_count += 1
                    
        print(f"    [✅] Found {ucl_filtered_count} Champions League fixtures involving PL clubs.")
    except Exception as e:
        print(f"    [⚠️] Could not parse Champions League calendar (Skipping UCL): {e}")

    total_to_scrape = len(target_fixtures)
    print(f"\n[🚀] Filtered scope complete. Total target fixtures to download: {total_to_scrape}")
    
    # Sort chronologically by timestamp
    sorted_match_ids = sorted(
        target_fixtures.keys(), 
        key=lambda m_id: target_fixtures[m_id].get('startTimestamp', 0)
    )

    all_raw_player_rows = []

    # Step 3: Request raw match statistics tables one-by-one
    for idx, match_id in enumerate(sorted_match_ids):
        match = target_fixtures[match_id]
        home_team = match.get('homeTeam', {}).get('name', 'Unknown')
        away_team = match.get('awayTeam', {}).get('name', 'Unknown')
        comp_source = match.get('origin_competition')
        
        ts = match.get('startTimestamp', 0)
        match_date = pd.to_datetime(ts, unit='s').strftime('%Y-%m-%d') if ts else "Unknown"
        
        print(f"    [{idx+1}/{total_to_scrape}] [{comp_source}] Raw Request: {match_date} | {home_team} vs {away_team}")
        
        try:
            # PURE REQUEST LAYER: Download the raw player match statistics matrix
            df_match_raw = scraper.scrape_player_match_stats(match_id)
            
            if df_match_raw is not None and not df_match_raw.empty:
                # Inject basic tracking headers
                df_match_raw['match_id'] = match_id
                df_match_raw['match_date'] = match_date
                df_match_raw['competition_source'] = comp_source
                df_match_raw['home_team_name'] = home_team
                df_match_raw['away_team_name'] = away_team
                
                all_raw_player_rows.append(df_match_raw)
            else:
                print(f"      [⚠️] Missing or empty data block returned for match ID {match_id}")
                
            # Buffer to avoid 503 limits
            time.sleep(delay)
            
        except Exception as e:
            print(f"      [❌] Skipping Match ID {match_id} due to network/scraping exception: {e}")
            time.sleep(delay * 2)

    # Step 4: Export to flat database layer
    if all_raw_player_rows:
        print("\n[*] Blending player tables and standardizing layout...")
        df_master_raw = pd.concat(all_raw_player_rows, ignore_index=True)
        df_master_raw = df_master_raw.loc[:, ~df_master_raw.columns.duplicated()].copy()
        
        df_master_raw.to_csv(output_file, index=False)
        print(f"\n[🚀] SUCCESS! DATASET GENERATED.")
        print(f"    -> Target File: {output_file}")
        print(f"    -> Total Extracted Rows (All Players for targeted games): {df_master_raw.shape[0]}")
    else:
        print("\n[❌] Execution ended: No rows were successfully collected.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract raw tables strictly centered around PL team involvements.")
    parser.add_argument("--year", default="23/24", help="SofaScore season format (e.g., 23/24)")
    parser.add_argument("--output-dir", default="Data_Raw_PL_Centric", help="Output folder")
    parser.add_argument("--delay", type=float, default=3.5, help="Throttle delay to prevent 503 errors")
    args = parser.parse_args()
    
    download_pl_centric_matches(
        year_ss=args.year,
        output_dir=args.output_dir,
        delay=args.delay
    )