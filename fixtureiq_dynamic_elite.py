#!/usr/bin/env python3
"""
FixtureIQ Dynamic Congestion Pipeline
========================================================================
Dynamically discovers teams and maps ALL domestic/European match loads.
========================================================================
"""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
import pandas as pd
import numpy as np

# Force Edge browser execution on Windows environments to bypass Cloudflare
os.environ["BOTASAURUS_CHROME_EXECUTABLE_PATH"] = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

try:
    import ScraperFC
    import soccerdata as sd
except ImportError as e:
    print(f"[-] Missing dependencies. Run: pip install ScraperFC soccerdata pandas numpy. Error: {e}")
    import sys
    sys.exit(1)


class FixtureIQDynamicPipeline:
    # A complete pool of target competitions involving English top-flight clubs
    COMPETITIONS_POOL = [
        "England Premier League",
        "UEFA Champions League",
        "UEFA Europa League",
        "UEFA Conference League",
        "FA Cup",
        "EFL Cup"
    ]

    def __init__(self, year_sofascore: str, output_dir: str, delay: float = 3.0):
        self.year_ss = year_sofascore  # Format: "23/24" or "24/25"
        self.delay = delay
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Anti-ban cache directory initialization
        self.cache_dir = Path(".fixtureiq_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        print("[*] Initializing ScraperFC Automation Engine...")
        self.scraper = ScraperFC.Sofascore()

    def discover_pl_teams(self) -> set[str]:
        """Dynamically extracts all teams that participated in the Premier League for the season."""
        print(f"\n[*] STEP 1: Dynamically discovering participating Premier League teams for season {self.year_ss}...")
        try:
            # Pulling the full league fixture list reveals every team involved
            pl_matches = self.scraper.get_match_dicts(self.year_ss, "England Premier League")
            discovered_teams = set()
            for match in pl_matches:
                home = match.get('homeTeam', {}).get('name')
                away = match.get('awayTeam', {}).get('name')
                if home: discovered_teams.add(home)
                if away: discovered_teams.add(away)
            
            print(f"[✅] Discovered {len(discovered_teams)} unique Premier League clubs: {list(discovered_teams)}")
            return discovered_teams
        except Exception as e:
            print(f"[❌] Critical error discovering Premier League teams: {e}")
            return set()

    def build_universal_fixtures(self, target_teams: set[str]) -> list[dict]:
        """Scans ALL competitions in the pool to find matches containing our target teams."""
        print("\n[*] STEP 2: Scanning all competitions for matches involving discovered teams...")
        universal_fixtures = []
        
        for comp in self.COMPETITIONS_POOL:
            try:
                print(f"    -> Scanning '{comp}' for season {self.year_ss}...")
                matches = self.scraper.get_match_dicts(self.year_ss, comp)
                
                comp_matches_count = 0
                for m in matches:
                    home_team = m.get('homeTeam', {}).get('name', '')
                    away_team = m.get('awayTeam', {}).get('name', '')
                    
                    # If either team belongs to our dynamically discovered list, keep the match
                    if home_team in target_teams or away_team in target_teams:
                        m["_target_competition"] = comp
                        universal_fixtures.append(m)
                        comp_matches_count += 1
                print(f"       [+] Retained {comp_matches_count} matching fixtures from {comp}")
                time.sleep(1) # Polite pause between calendar indexes
            except Exception as e:
                # Some competitions (like Conference League) might not feature English teams in specific years
                print(f"       [⚠️] Competition '{comp}' not available or skipped: {e}")

        # Sort the entire multi-league calendar chronologically using Unix timestamps
        universal_fixtures = sorted(universal_fixtures, key=lambda x: x.get('startTimestamp', 0))
        print(f"[✅] Completed full integration: Isolated {len(universal_fixtures)} total matches cross-league.")
        return universal_fixtures

    def fetch_match_player_stats_with_cache(self, match_id: int) -> pd.DataFrame | None:
        """Reads local cache to save time and avoid API blocks; falls back to scraping if missing."""
        cache_file = self.cache_dir / f"match_{match_id}.csv"
        if cache_file.exists():
            return pd.read_csv(cache_file)
            
        try:
            time.sleep(self.delay)
            df_match = self.scraper.scrape_player_match_stats(match_id)
            if df_match is not None and not df_match.empty:
                df_match = df_match.reset_index(drop=True)
                df_match = df_match.loc[:, ~df_match.columns.duplicated()].copy()
                df_match.to_csv(cache_file, index=False)
                return df_match
        except Exception as e:
            print(f"      [⚠️] Scraping exception on Match ID {match_id}: {e}")
        return None

    def execute_pipeline(self) -> pd.DataFrame:
        # Step 1: Discover who is playing this season
        pl_teams = self.discover_pl_teams()
        if not pl_teams:
            return pd.DataFrame()
            
        # Step 2: Grab every match from every league involving those teams
        fixtures = self.build_universal_fixtures(pl_teams)
        if not fixtures:
            return pd.DataFrame()
            
        all_compiled_records = []
        print("\n[*] STEP 3: Processing player performance matrix match-by-match...")
        
        for idx, match in enumerate(fixtures):
            match_id = match.get('id')
            comp = match.get('_target_competition')
            home_team = match.get('homeTeam', {}).get('name', 'Unknown')
            away_team = match.get('awayTeam', {}).get('name', 'Unknown')
            
            ts = match.get('startTimestamp') or match.get('status', {}).get('startTimestamp', 0)
            match_date = pd.to_datetime(ts, unit='s').strftime('%Y-%m-%d')
            
            print(f"    [{idx+1}/{len(fixtures)}] [{comp}] {match_date} | {home_team} vs {away_team}")
            
            df_match = self.fetch_match_player_stats_with_cache(match_id)
            if df_match is None or df_match.empty:
                continue
                
            df_match['match_id'] = match_id
            df_match['match_date_str'] = match_date
            df_match['competition'] = comp
            df_match['home_team_name'] = home_team
            df_match['away_team_name'] = away_team
            
            all_compiled_records.append(df_match)
            
        if not all_compiled_records:
            return pd.DataFrame()
            
        df_master = pd.concat(all_compiled_records, ignore_index=True)
        df_master['date'] = pd.to_datetime(df_master['match_date_str'])
        
        player_col = next((c for c in ['player_name', 'player', 'name'] if c in df_master.columns), df_master.columns[0])
        
        # --- STEP 4: Advanced Cross-Competition Feature Engineering ---
        print("\n[*] STEP 4: Engineering time-series fatigue workloads across all tournaments...")
        df_master = df_master.sort_values(by=[player_col, 'date']).reset_index(drop=True)
        
        # Rest calculation now perfectly includes FA Cup, League Cup, and European nights
        df_master['rest_days'] = df_master.groupby(player_col)['date'].diff().dt.days
        df_master['rest_days'] = df_master['rest_days'].fillna(14).astype(int)
        df_master['high_congestion_flag'] = np.where(df_master['rest_days'] <= 3, 1, 0)
        
        df_master.set_index('date', inplace=True)
        if 'minutesPlayed' in df_master.columns:
            df_master['minutesPlayed'] = df_master['minutesPlayed'].fillna(0).astype(int)
            df_master['min_last_7d'] = df_master.groupby(player_col)['minutesPlayed'].rolling('7D', closed='left').sum().reset_index(0, drop=True)
            df_master['min_last_28d'] = df_master.groupby(player_col)['minutesPlayed'].rolling('28D', closed='left').sum().reset_index(0, drop=True)
        df_master.reset_index(inplace=True)
        
        df_master['min_last_7d'] = df_master['min_last_7d'].fillna(0).astype(int)
        df_master['min_last_28d'] = df_master['min_last_28d'].fillna(0).astype(int)
        
        df_master['acwr_ratio'] = np.where(
            df_master['min_last_28d'] > 0, 
            df_master['min_last_7d'] / (df_master['min_last_28d'] / 4.0), 
            0.0
        )
        
        if 'duelsWon' in df_master.columns and 'duelsLost' in df_master.columns:
            t_duels = df_master['duelsWon'].fillna(0) + df_master['duelsLost'].fillna(0)
            df_master['duel_success_pct'] = np.where(t_duels > 0, (df_master['duelsWon'] / t_duels) * 100, 0)
            
        if 'possessionLostCtrl' in df_master.columns and 'minutesPlayed' in df_master.columns:
            df_master['turnovers_per_90min'] = np.where(df_master['minutesPlayed'] > 0, (df_master['possessionLostCtrl'] / df_master['minutesPlayed']) * 90, 0)

        # --- STEP 5: SoccerData Context Matching ---
        print("\n[*] STEP 5: Stitching contextual data via SoccerData...")
        try:
            elo_client = sd.ClubElo()
            df_elo = elo_client.read_by_date()
            
            # Flatten MultiIndex and standardize column names to lowercase
            df_elo = df_elo.reset_index()
            df_elo.columns = [str(c).lower() for c in df_elo.columns]
            
            # Map known naming variances between SofaScore strings and ClubELO records
            team_map = {
                "Brighton & Hove Albion": "Brighton",
                "Newcastle United": "Newcastle",
                "Liverpool FC": "Liverpool",
                "Nottingham Forest": "Nottingham Forest",
                "Brentford": "Brentford",
                "West Ham United": "West Ham",
                "Bournemouth": "Bournemouth",
                "Leicester City": "Leicester",
                "Chelsea": "Chelsea",
                "Wolverhampton": "Wolves",
                "Southampton": "Southampton",
                "Crystal Palace": "Crystal Palace",
                "Ipswich Town": "Ipswich",
                "Manchester City": "Man City",
                "Fulham": "Fulham",
                "Everton": "Everton",
                "Tottenham Hotspur": "Tottenham",
                "Manchester United": "Man United",
                "Aston Villa": "Aston Villa",
                "Arsenal": "Arsenal"
            }
            df_master['teamName_elo'] = df_master['teamName'].replace(team_map)

            # Ensure all timeline arrays are formatted as datetime types
            df_elo['from'] = pd.to_datetime(df_elo['from'])
            df_elo['to'] = pd.to_datetime(df_elo['to'])
            
            # Initialize the column with a default placeholder float value
            df_master['elo'] = np.nan
            
            print("    -> Processing interval date alignment blocks...")
            # Step through unique teams in your current batch to keep processing extremely efficient
            for unique_team in df_master['teamName_elo'].unique():
                # Isolate the ELO historical timeline maps for this specific club
                team_elo_hist = df_elo[df_elo['team'] == unique_team]
                if team_elo_hist.empty:
                    continue
                    
                # Filter down your master dataset rows belonging to this club
                master_team_mask = df_master['teamName_elo'] == unique_team
                team_match_dates = df_master.loc[master_team_mask, 'date']
                
                # Align exact historical ELO intervals for each individual match date
                elo_values = []
                for m_date in team_match_dates:
                    # Find the row where the match date is between the 'from' and 'to' range
                    matched_row = team_elo_hist[(team_elo_hist['from'] <= m_date) & (team_elo_hist['to'] >= m_date)]
                    if not matched_row.empty:
                        elo_values.append(matched_row['elo'].values[0])
                    else:
                        # Fallback to closest available record if there's a minor schedule gap
                        closest_row = team_elo_hist.iloc[(team_elo_hist['from'] - m_date).abs().argsort()[:1]]
                        elo_values.append(closest_row['elo'].values[0] if not closest_row.empty else np.nan)
                        
                df_master.loc[master_team_mask, 'elo'] = elo_values
                
            print("    [✅] ClubELO chronological timeline boundaries stitched successfully!")
            
        except Exception as e:
            print(f"    [⚠️] Context expansion skipped: {e}")

        # Drop the temporary mapping helper column before final delivery
        if 'teamName_elo' in df_master.columns:
            df_master = df_master.drop(columns=['teamName_elo'])

        return df_master

    def export(self, df: pd.DataFrame):
        if df.empty: return
        df.to_csv(self.output_dir / "fixtureiq_dynamic_master.csv", index=False)
        
        features = [
            'match_date_str', 'match_id', 'competition', 'teamName', 'player_name', 'name', 'position', 'rating', 'elo',
            'minutesPlayed', 'rest_days', 'high_congestion_flag', 'min_last_7d', 'acwr_ratio', 'duel_success_pct', 'turnovers_per_90min'
        ]
        valid_features = [f for f in features if f in df.columns]
        df_clean = df[valid_features]
        if 'position' in df_clean.columns:
            df_clean = df_clean[df_clean['position'] != 'G']
            
        df_clean.to_csv(self.output_dir / "fixtureiq_dynamic_analytics_clean.csv", index=False)
        print(f"\n[🚀] SUCCESSFUL DYNAMIC GENERATION!")
        print(f"    -> Target Output Location: {self.output_dir / 'fixtureiq_dynamic_analytics_clean.csv'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FixtureIQ Fully Dynamic Season Mapper")
    parser.add_argument("--year", default="23/24", help="SofaScore short season code (e.g. 23/24)")
    parser.add_argument("--output-dir", default="Data_Dynamic", help="Export folder")
    args = parser.parse_args()
    
    pipeline = FixtureIQDynamicPipeline(year_sofascore=args.year, output_dir=args.output_dir)
    master_df = pipeline.execute_pipeline()
    pipeline.export(master_df)